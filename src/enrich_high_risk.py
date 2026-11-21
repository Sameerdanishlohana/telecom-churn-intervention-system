"""
Enriches High-Risk customers in FactRetentionAction with live OpenRouter / DeepSeek outputs.
"""
from sqlalchemy import create_engine, text
import pandas as pd
from config import get_db_url
from llm_explainer import generate_llm_explanation

def enrich_high_risk():
    engine = create_engine(get_db_url())
    query = """
        SELECT r.ActionKey, c.CustomerID, r.RiskScore, r.RiskLevel, r.RecommendedAction
        FROM FactRetentionAction r
        JOIN DimCustomer c ON r.CustomerKey = c.CustomerKey
        WHERE r.RiskLevel = 'High'
    """
    df_high = pd.read_sql(query, engine)
    print(f"Enriching {len(df_high)} High-Risk customers with live OpenRouter DeepSeek...")

    with engine.begin() as conn:
        for idx, row in df_high.iterrows():
            dec = {
                "CustomerID": row["CustomerID"],
                "RiskScore": row["RiskScore"],
                "RiskLevel": row["RiskLevel"],
                "RecommendedAction": row["RecommendedAction"],
                "ContributingFactors": "Month-to-month contract, High monthly bill, Electronic check, Missing security add-on"
            }
            res = generate_llm_explanation(dec)
            conn.execute(text("""
                UPDATE FactRetentionAction
                SET LLMExplanation = :exp,
                    DraftCustomerMessage = :draft,
                    ModelName = :model
                WHERE ActionKey = :k
            """), {
                "exp": res["LLMExplanation"],
                "draft": res["DraftCustomerMessage"],
                "model": res["ModelName"],
                "k": row["ActionKey"]
            })
            if (idx + 1) % 15 == 0 or (idx + 1) == len(df_high):
                print(f" - Enriched {idx + 1}/{len(df_high)} records")

    print("[SUCCESS] All High-Risk customer records enriched with live DeepSeek explanations and messages!")

if __name__ == "__main__":
    enrich_high_risk()

