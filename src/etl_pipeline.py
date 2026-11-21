"""
End-to-End Multi-Layer ETL Pipeline for Telecom Churn Intervention System.
FAST NUCES Karachi - DWBI (BDS-5B)

Orchestration Layers:
1. Extract: Ingest CSVs (Primary IBM Telco, Synthetic Support Tickets, Synthetic Plans)
2. Staging & Bronze: Raw load into MySQL staging tables (stg_customers, stg_tickets, stg_plans) and bronze directory.
3. Silver Layer: Clean, cast types (handle blank TotalCharges -> 0.00), standardize Yes/No, create TenureBands and surrogate keys.
4. Gold Layer (Warehouse Load):
   - Outrigger: DimServiceCategory
   - Dimensions: DimService, DimCustomer, DimContract, DimPayment, DimSnapshotDate
   - Facts: FactCustomerChurn, FactCustomerService
5. Post-load Reconciliation & Verification: Row counts, audit check.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent))
from config import (
    RAW_DATA_DIR, BRONZE_DATA_DIR, SILVER_DATA_DIR, GOLD_DATA_DIR,
    ETL_SNAPSHOT_DATE, LOAD_BATCH_ID, get_db_url
)


def run_pipeline():
    print("=" * 70)
    print("TELECOM CHURN INTERVENTION SYSTEM - ETL PIPELINE")
    print(f"Batch ID: {LOAD_BATCH_ID} | Snapshot Date: {ETL_SNAPSHOT_DATE}")
    print("=" * 70)

    engine = create_engine(get_db_url())

    # -------------------------------------------------------------------------
    # STEP 1: EXTRACT & BRONZE LOAD
    # -------------------------------------------------------------------------
    print("\n>>> [1/5] Extracting Source Datasets...")
    cust_file = RAW_DATA_DIR / "Telco-Customer-Churn.csv"
    ticket_file = RAW_DATA_DIR / "synthetic_support_tickets.csv"
    plan_file = RAW_DATA_DIR / "synthetic_plans_tariffs.csv"

    for f in [cust_file, ticket_file, plan_file]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required input file: {f}")

    df_raw_cust = pd.read_csv(cust_file)
    df_raw_tickets = pd.read_csv(ticket_file)
    df_raw_plans = pd.read_csv(plan_file)

    print(f" - Primary Customers: {df_raw_cust.shape[0]} rows, {df_raw_cust.shape[1]} cols")
    print(f" - Synthetic Tickets: {df_raw_tickets.shape[0]} rows, {df_raw_tickets.shape[1]} cols")
    print(f" - Synthetic Plans:   {df_raw_plans.shape[0]} rows, {df_raw_plans.shape[1]} cols")

    # Bronze exports (raw unchanged backups)
    df_raw_cust.to_csv(BRONZE_DATA_DIR / "bronze_customers.csv", index=False)
    df_raw_tickets.to_csv(BRONZE_DATA_DIR / "bronze_tickets.csv", index=False)
    df_raw_plans.to_csv(BRONZE_DATA_DIR / "bronze_plans.csv", index=False)

    # -------------------------------------------------------------------------
    # STEP 2: LOAD INTO STAGING TABLES (MySQL)
    # -------------------------------------------------------------------------
    print("\n>>> [2/5] Loading Staging Layer in MySQL...")
    df_stg_cust = df_raw_cust.copy()
    df_stg_cust["LoadBatchID"] = LOAD_BATCH_ID
    
    df_stg_tickets = df_raw_tickets.copy()
    df_stg_tickets["LoadBatchID"] = LOAD_BATCH_ID

    df_stg_plans = df_raw_plans.copy()
    df_stg_plans["LoadBatchID"] = LOAD_BATCH_ID

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE stg_customers;"))
        conn.execute(text("TRUNCATE TABLE stg_tickets;"))
        conn.execute(text("TRUNCATE TABLE stg_plans;"))

    df_stg_cust.to_sql("stg_customers", engine, if_exists="append", index=False)
    df_stg_tickets.to_sql("stg_tickets", engine, if_exists="append", index=False)
    df_stg_plans.to_sql("stg_plans", engine, if_exists="append", index=False)
    print(" [+] Staging tables successfully populated.")

    # -------------------------------------------------------------------------
    # STEP 3: SILVER LAYER TRANSFORMATIONS
    # -------------------------------------------------------------------------
    print("\n>>> [3/5] Transforming into Silver Layer...")
    df_silver_cust = df_raw_cust.copy()

    # 3.1 Clean and cast TotalCharges
    df_silver_cust["TotalCharges"] = pd.to_numeric(
        df_silver_cust["TotalCharges"].astype(str).str.strip(), errors="coerce"
    )
    blank_tc_count = df_silver_cust["TotalCharges"].isna().sum()
    print(f" - Handled {blank_tc_count} blank TotalCharges values -> Coerced to 0.00")
    df_silver_cust["TotalCharges"] = df_silver_cust["TotalCharges"].fillna(0.00)

    # 3.2 Ensure MonthlyCharges is numeric
    df_silver_cust["MonthlyCharges"] = pd.to_numeric(df_silver_cust["MonthlyCharges"], errors="coerce")

    # 3.3 Churn Flag derivation
    df_silver_cust["ChurnFlag"] = df_silver_cust["Churn"].apply(
        lambda x: 1 if str(x).strip().lower() == "yes" else 0
    )

    # 3.4 Tenure Band derivation
    def categorize_tenure(t):
        if t <= 12:
            return "0-12 Months"
        elif t <= 24:
            return "13-24 Months"
        elif t <= 48:
            return "25-48 Months"
        else:
            return "49+ Months"

    df_silver_cust["TenureBand"] = df_silver_cust["tenure"].apply(categorize_tenure)

    # 3.5 Payment classification
    def get_payment_type(pm):
        pm_lower = str(pm).lower()
        if "automatic" in pm_lower:
            return "Auto"
        elif "check" in pm_lower:
            return "Check"
        else:
            return "Manual"

    def get_autopay_flag(pm):
        return 1 if "automatic" in str(pm).lower() else 0

    df_silver_cust["PaymentType"] = df_silver_cust["PaymentMethod"].apply(get_payment_type)
    df_silver_cust["AutoPayFlag"] = df_silver_cust["PaymentMethod"].apply(get_autopay_flag)

    df_silver_cust.to_csv(SILVER_DATA_DIR / "silver_customers.csv", index=False)
    print(f" [+] Silver layer processed: {df_silver_cust.shape[0]} records.")

    # -------------------------------------------------------------------------
    # STEP 4: GOLD / WAREHOUSE DIMENSIONAL LOAD
    # -------------------------------------------------------------------------
    print("\n>>> [4/5] Populating Warehouse Dimensions and Facts...")
    snapshot_dt = datetime.strptime(ETL_SNAPSHOT_DATE, "%Y-%m-%d")
    date_key = int(snapshot_dt.strftime("%Y%m%d"))

    with engine.begin() as conn:
        # Disable FK checks to allow clean idempotent loads
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        conn.execute(text("TRUNCATE TABLE FactRetentionAction;"))
        conn.execute(text("TRUNCATE TABLE FactCustomerService;"))
        conn.execute(text("TRUNCATE TABLE FactCustomerChurn;"))
        conn.execute(text("TRUNCATE TABLE DimService;"))
        conn.execute(text("TRUNCATE TABLE DimServiceCategory;"))
        conn.execute(text("TRUNCATE TABLE DimSnapshotDate;"))
        conn.execute(text("TRUNCATE TABLE DimPayment;"))
        conn.execute(text("TRUNCATE TABLE DimContract;"))
        conn.execute(text("TRUNCATE TABLE DimCustomer;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    # 4.1 DimSnapshotDate
    df_snapshot = pd.DataFrame([{
        "SnapshotDateKey": date_key,
        "SnapshotDate": ETL_SNAPSHOT_DATE,
        "Year": snapshot_dt.year,
        "Month": snapshot_dt.month,
        "Quarter": (snapshot_dt.month - 1) // 3 + 1,
        "LoadBatchID": LOAD_BATCH_ID
    }])
    df_snapshot.to_sql("DimSnapshotDate", engine, if_exists="append", index=False)

    # 4.2 DimCustomer
    df_dim_customer = df_silver_cust[[
        "customerID", "gender", "SeniorCitizen", "Partner", "Dependents"
    ]].drop_duplicates().rename(columns={
        "customerID": "CustomerID",
        "gender": "Gender"
    })
    df_dim_customer.to_sql("DimCustomer", engine, if_exists="append", index=False)

    # 4.3 DimContract
    df_dim_contract = df_silver_cust[[
        "Contract", "PaperlessBilling", "TenureBand"
    ]].drop_duplicates().rename(columns={"Contract": "ContractType"}).reset_index(drop=True)
    df_dim_contract.to_sql("DimContract", engine, if_exists="append", index=False)

    # 4.4 DimPayment
    df_dim_payment = df_silver_cust[[
        "PaymentMethod", "PaymentType", "AutoPayFlag"
    ]].drop_duplicates().reset_index(drop=True)
    df_dim_payment.to_sql("DimPayment", engine, if_exists="append", index=False)

    # 4.5 Snowflaked Service Dimension: DimServiceCategory & DimService
    categories = [
        {"CategoryName": "Phone"},
        {"CategoryName": "Internet"},
        {"CategoryName": "Security/Support"},
        {"CategoryName": "Streaming"}
    ]
    pd.DataFrame(categories).to_sql("DimServiceCategory", engine, if_exists="append", index=False)

    # Read back Category keys
    cat_map = pd.read_sql("SELECT ServiceCategoryKey, CategoryName FROM DimServiceCategory", engine)
    cat_dict = dict(zip(cat_map["CategoryName"], cat_map["ServiceCategoryKey"]))

    service_definitions = [
        # Phone
        {"ServiceName": "PhoneService", "ServiceOption": "Single Line", "ServiceCategoryKey": cat_dict["Phone"]},
        {"ServiceName": "MultipleLines", "ServiceOption": "Multiple Lines", "ServiceCategoryKey": cat_dict["Phone"]},
        # Internet
        {"ServiceName": "InternetService_DSL", "ServiceOption": "DSL", "ServiceCategoryKey": cat_dict["Internet"]},
        {"ServiceName": "InternetService_Fiber", "ServiceOption": "Fiber optic", "ServiceCategoryKey": cat_dict["Internet"]},
        # Security/Support
        {"ServiceName": "OnlineSecurity", "ServiceOption": "Online Security", "ServiceCategoryKey": cat_dict["Security/Support"]},
        {"ServiceName": "OnlineBackup", "ServiceOption": "Online Backup", "ServiceCategoryKey": cat_dict["Security/Support"]},
        {"ServiceName": "DeviceProtection", "ServiceOption": "Device Protection", "ServiceCategoryKey": cat_dict["Security/Support"]},
        {"ServiceName": "TechSupport", "ServiceOption": "Tech Support", "ServiceCategoryKey": cat_dict["Security/Support"]},
        # Streaming
        {"ServiceName": "StreamingTV", "ServiceOption": "Streaming TV", "ServiceCategoryKey": cat_dict["Streaming"]},
        {"ServiceName": "StreamingMovies", "ServiceOption": "Streaming Movies", "ServiceCategoryKey": cat_dict["Streaming"]},
    ]
    pd.DataFrame(service_definitions).to_sql("DimService", engine, if_exists="append", index=False)

    # -------------------------------------------------------------------------
    # Read back dimension surrogate keys for Fact construction
    # -------------------------------------------------------------------------
    db_customers = pd.read_sql("SELECT CustomerKey, CustomerID FROM DimCustomer", engine)
    db_contracts = pd.read_sql("SELECT ContractKey, ContractType, PaperlessBilling, TenureBand FROM DimContract", engine)
    db_payments = pd.read_sql("SELECT PaymentKey, PaymentMethod, PaymentType, AutoPayFlag FROM DimPayment", engine)
    db_services = pd.read_sql("SELECT ServiceKey, ServiceName, ServiceOption FROM DimService", engine)

    # Build FactCustomerChurn
    df_fact_churn = df_silver_cust.merge(
        db_customers, left_on="customerID", right_on="CustomerID"
    ).merge(
        db_contracts, left_on=["Contract", "PaperlessBilling", "TenureBand"],
        right_on=["ContractType", "PaperlessBilling", "TenureBand"]
    ).merge(
        db_payments, left_on=["PaymentMethod", "PaymentType", "AutoPayFlag"],
        right_on=["PaymentMethod", "PaymentType", "AutoPayFlag"]
    )

    df_fact_churn["SnapshotDateKey"] = date_key
    df_fact_churn["TenureMonths"] = df_fact_churn["tenure"]
    df_fact_churn["RiskScore"] = 0  # To be enriched by Intelligent Agent in Phase 5

    churn_cols = [
        "CustomerKey", "ContractKey", "PaymentKey", "SnapshotDateKey",
        "TenureMonths", "MonthlyCharges", "TotalCharges", "ChurnFlag", "RiskScore"
    ]
    df_fact_churn_insert = df_fact_churn[churn_cols]
    df_fact_churn_insert.to_sql("FactCustomerChurn", engine, if_exists="append", index=False)
    print(f" [+] FactCustomerChurn loaded: {len(df_fact_churn_insert)} rows.")

    # Build FactCustomerService
    print(" - Constructing FactCustomerService bridge...")
    service_fact_records = []
    service_key_map = dict(zip(db_services["ServiceName"], db_services["ServiceKey"]))

    for _, row in df_silver_cust.iterrows():
        c_key = db_customers.loc[db_customers["CustomerID"] == row["customerID"], "CustomerKey"].values[0]

        # Phone
        active_ph = 1 if str(row["PhoneService"]).lower() == "yes" else 0
        service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map["PhoneService"], "SnapshotDateKey": date_key, "ActiveFlag": active_ph})

        active_ml = 1 if str(row["MultipleLines"]).lower() == "yes" else 0
        service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map["MultipleLines"], "SnapshotDateKey": date_key, "ActiveFlag": active_ml})

        # Internet
        is_val = str(row["InternetService"]).lower()
        service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map["InternetService_DSL"], "SnapshotDateKey": date_key, "ActiveFlag": 1 if "dsl" in is_val else 0})
        service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map["InternetService_Fiber"], "SnapshotDateKey": date_key, "ActiveFlag": 1 if "fiber" in is_val else 0})

        # Security/Support
        for s_col in ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport"]:
            act = 1 if str(row[s_col]).lower() == "yes" else 0
            service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map[s_col], "SnapshotDateKey": date_key, "ActiveFlag": act})

        # Streaming
        for st_col in ["StreamingTV", "StreamingMovies"]:
            act = 1 if str(row[st_col]).lower() == "yes" else 0
            service_fact_records.append({"CustomerKey": c_key, "ServiceKey": service_key_map[st_col], "SnapshotDateKey": date_key, "ActiveFlag": act})

    df_fact_service = pd.DataFrame(service_fact_records)
    df_fact_service.to_sql("FactCustomerService", engine, if_exists="append", index=False, chunksize=10000)
    print(f" [+] FactCustomerService loaded: {len(df_fact_service)} rows.")

    # -------------------------------------------------------------------------
    # STEP 5: POST-LOAD RECONCILIATION AUDIT
    # -------------------------------------------------------------------------
    print("\n>>> [5/5] Performing Post-Load Reconciliation Audit...")
    with engine.connect() as conn:
        stg_cnt = conn.execute(text("SELECT COUNT(*) FROM stg_customers;")).scalar()
        dim_cust_cnt = conn.execute(text("SELECT COUNT(*) FROM DimCustomer;")).scalar()
        fact_churn_cnt = conn.execute(text("SELECT COUNT(*) FROM FactCustomerChurn;")).scalar()
        fact_service_cnt = conn.execute(text("SELECT COUNT(*) FROM FactCustomerService;")).scalar()
        mart_cust_cnt = conn.execute(text("SELECT COUNT(*) FROM vw_CustomerMart;")).scalar()
        total_rev = conn.execute(text("SELECT ROUND(SUM(MonthlyCharges), 2) FROM FactCustomerChurn;")).scalar()
        churned_rev = conn.execute(text("SELECT ROUND(SUM(MonthlyCharges), 2) FROM FactCustomerChurn WHERE ChurnFlag = 1;")).scalar()
        churn_pct = conn.execute(text("SELECT ROUND(AVG(ChurnFlag)*100, 2) FROM FactCustomerChurn;")).scalar()

    print(f" - Staging Customer Rows:        {stg_cnt}")
    print(f" - DimCustomer Rows:             {dim_cust_cnt}")
    print(f" - FactCustomerChurn Rows:       {fact_churn_cnt}")
    print(f" - FactCustomerService Rows:     {fact_service_cnt}")
    print(f" - Customer Mart View Rows:      {mart_cust_cnt}")
    print(f" - Total Monthly Revenue:        ${total_rev:,.2f}")
    print(f" - Churned Monthly Revenue:      ${churned_rev:,.2f}")
    print(f" - Overall Churn Rate:           {churn_pct}%")

    if stg_cnt == dim_cust_cnt == fact_churn_cnt:
        print("\n[SUCCESS] 100% Data Reconciliation achieved across all warehouse layers!")
    else:
        print("\n[WARNING] Row count mismatch detected!")

    return True


if __name__ == "__main__":
    run_pipeline()
