"""
ETL Pipeline for Telecom Churn Intervention System.
Orchestrates:
1. Extract (CSV -> Staging)
2. Transform & Standardize (Cleaning, Type Casting, Surrogate Key creation)
3. Load to Bronze, Silver, and Gold warehouse layers.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parent))
from config import (
    RAW_DATA_DIR, BRONZE_DATA_DIR, SILVER_DATA_DIR, GOLD_DATA_DIR,
    ETL_SNAPSHOT_DATE, LOAD_BATCH_ID
)


def run_etl():
    print("=" * 60)
    print(f"Starting Telecom Churn ETL Pipeline | Batch: {LOAD_BATCH_ID}")
    print(f"Snapshot Date: {ETL_SNAPSHOT_DATE}")
    print("=" * 60)

    # 1. Verification of raw files
    customer_file = RAW_DATA_DIR / "Telco-Customer-Churn.csv"
    ticket_file = RAW_DATA_DIR / "synthetic_support_tickets.csv"
    plan_file = RAW_DATA_DIR / "synthetic_plans_tariffs.csv"

    if not customer_file.exists():
        print(f"[!] Primary customer file missing at: {customer_file}")
        return False

    # Extract
    df_raw_cust = pd.read_csv(customer_file)
    print(f"[EXTRACT] Raw Customers shape: {df_raw_cust.shape}")

    # Bronze write-through (unmodified raw copy)
    df_raw_cust.to_csv(BRONZE_DATA_DIR / "bronze_customers.csv", index=False)

    # Transform: TotalCharges conversion, handle spaces/nulls
    df_cust = df_raw_cust.copy()
    df_cust["TotalCharges"] = pd.to_numeric(df_cust["TotalCharges"].astype(str).str.strip(), errors="coerce")
    null_tc = df_cust["TotalCharges"].isna().sum()
    print(f"[TRANSFORM] Found {null_tc} blank TotalCharges records (tenure == 0). Coercing to 0.0.")
    df_cust["TotalCharges"] = df_cust["TotalCharges"].fillna(0.0)

    # Standardize ChurnFlag
    df_cust["ChurnFlag"] = df_cust["Churn"].apply(lambda x: 1 if str(x).strip().lower() == "yes" else 0)

    # Tenure Bands
    def get_tenure_band(t):
        if t <= 12:
            return "0-12 Months"
        elif t <= 24:
            return "13-24 Months"
        elif t <= 48:
            return "25-48 Months"
        else:
            return "49+ Months"

    df_cust["TenureBand"] = df_cust["tenure"].apply(get_tenure_band)
    df_cust["SnapshotDate"] = ETL_SNAPSHOT_DATE
    df_cust["LoadBatchID"] = LOAD_BATCH_ID

    # Save to Silver
    df_cust.to_csv(SILVER_DATA_DIR / "silver_customers.csv", index=False)
    print(f"[LOAD] Silver customer layer written: {df_cust.shape}")

    # Gold Layer transformations (Facts and Dimensions) will follow in Phase 3
    print("[+] Phase 1 ETL scaffolding initialized successfully.")
    return True


if __name__ == "__main__":
    run_etl()

