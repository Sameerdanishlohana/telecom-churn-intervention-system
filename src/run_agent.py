"""
Execution and Write-Back Engine for the Intelligent Agent and LLM Explainer.
Reads customer profiles and support logs from MySQL Gold Marts, runs rule scoring,
generates explanations, updates FactCustomerChurn.RiskScore, and writes back into FactRetentionAction.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parent))
from config import get_db_url, ETL_SNAPSHOT_DATE
from retention_agent import RetentionAgent
from llm_explainer import generate_llm_explanation


def run_agent_and_writeback():
    print("=" * 70)
    print("INTELLIGENT AGENT & LLM WRITE-BACK PIPELINE")
    print("=" * 70)

    engine = create_engine(get_db_url())

    # 1. Perceive: Read Customer Mart and Support Tickets from Database
    print("\n>>> [1/4] Perceiving Customer & Support Data from MySQL...")
    df_mart = pd.read_sql("SELECT * FROM vw_CustomerMart", engine)
    df_raw = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "silver" / "silver_customers.csv")
    df_tickets = pd.read_sql("SELECT CustomerID, COUNT(*) AS TicketCount FROM stg_tickets GROUP BY CustomerID", engine)

    # Merge service features from silver
    service_cols = [
        "customerID", "InternetService", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"
    ]
    df_merged = df_mart.merge(df_raw[service_cols], left_on="CustomerID", right_on="customerID", how="left")
    df_merged = df_merged.merge(df_tickets, on="CustomerID", how="left").fillna({"TicketCount": 0})
    print(f" [+] Perceived {len(df_merged)} active customer records.")

    # 2. Reason: Score Risk via Heuristic Rule Engine
    print("\n>>> [2/4] Reasoning & Applying Decision Matrix...")
    agent = RetentionAgent()
    evaluations = []

    for _, row in df_merged.iterrows():
        row_dict = row.to_dict()
        decision = agent.evaluate_customer(row_dict, ticket_count=int(row["TicketCount"]))
        decision["CustomerKey"] = row["CustomerKey"]
        evaluations.append(decision)

    df_evals = pd.DataFrame(evaluations)
    print(" [+] Risk Level Breakdown:")
    print(df_evals["RiskLevel"].value_counts())
    print("\n [+] Top Recommended Actions:")
    print(df_evals["RecommendedAction"].value_counts())

    # 3. LLM Explanations (Sampling / Generating explainability & draft messages)
    print("\n>>> [3/4] Generating Human-in-the-Loop Explanations & Draft Offers...")
    explanations = []
    drafts = []
    models = []

    for _, dec in df_evals.iterrows():
        llm_out = generate_llm_explanation(dec.to_dict())
        explanations.append(llm_out["LLMExplanation"])
        drafts.append(llm_out["DraftCustomerMessage"])
        models.append(llm_out["ModelName"])

    df_evals["LLMExplanation"] = explanations
    df_evals["DraftCustomerMessage"] = drafts
    df_evals["ModelName"] = models
    df_evals["RunDate"] = ETL_SNAPSHOT_DATE

    # 4. Act: Write-back to MySQL Warehouse
    print("\n>>> [4/4] Writing Back AI Results to FactRetentionAction & FactCustomerChurn...")
    
    # 4.1 Insert into FactRetentionAction
    insert_cols = [
        "CustomerKey", "RiskScore", "RiskLevel", "RecommendedAction",
        "LLMExplanation", "DraftCustomerMessage", "RuleVersion", "RunDate", "ModelName"
    ]
    df_insert = df_evals[insert_cols]
    
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE FactRetentionAction;"))
        
    df_insert.to_sql("FactRetentionAction", engine, if_exists="append", index=False, chunksize=5000)
    print(f" [+] Successfully wrote {len(df_insert)} decision records into FactRetentionAction.")

    # 4.2 Update FactCustomerChurn RiskScore
    print(" - Synchronizing RiskScore into FactCustomerChurn...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE FactCustomerChurn f
            JOIN FactRetentionAction r ON f.CustomerKey = r.CustomerKey
            SET f.RiskScore = r.RiskScore;
        """))

    # Verification
    with engine.connect() as conn:
        retention_cnt = conn.execute(text("SELECT COUNT(*) FROM FactRetentionAction;")).scalar()
        high_risk_rev = conn.execute(text("""
            SELECT ROUND(SUM(f.MonthlyCharges), 2) 
            FROM FactCustomerChurn f
            JOIN FactRetentionAction r ON f.CustomerKey = r.CustomerKey
            WHERE r.RiskLevel = 'High';
        """)).scalar()
        high_risk_actual_churn = conn.execute(text("""
            SELECT ROUND(AVG(f.ChurnFlag)*100, 2)
            FROM FactCustomerChurn f
            JOIN FactRetentionAction r ON f.CustomerKey = r.CustomerKey
            WHERE r.RiskLevel = 'High';
        """)).scalar()

    print(f"\n[AUDIT] FactRetentionAction Rows: {retention_cnt}")
    print(f"[AUDIT] Monthly Revenue at High Risk: ${high_risk_rev:,.2f}")
    print(f"[AUDIT] Actual Churn Rate among High Risk Group: {high_risk_actual_churn}% (vs 26.54% overall)")
    print("[SUCCESS] Agent & LLM write-back completed successfully!")
    return True


if __name__ == "__main__":
    run_agent_and_writeback()

