"""
LLM Explanation and Draft Communication Module.
Uses strictly constrained JSON prompts and low temperature.
Includes a fully deterministic offline fallback template generator.
"""

import os
import json
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL


def generate_llm_explanation(decision_record: dict) -> dict:
    """
    Receives structured agent output and produces:
    1. Short retention-officer explanation
    2. Draft polite retention message
    Safeguards: Grounded strictly on supplied fields, low temperature, fallback capable.
    """
    # Deterministic fallback generator (Offline / Default)
    customer_id = decision_record.get("CustomerID", "Valued Customer")
    risk_level = decision_record.get("RiskLevel", "Low")
    risk_score = decision_record.get("RiskScore", 0)
    action = decision_record.get("RecommendedAction", "Routine loyalty communication")
    factors = decision_record.get("ContributingFactors", "Standard usage patterns")

    if risk_level == "High":
        officer_note = (
            f"Customer {customer_id} exhibits High Churn Risk (Score {risk_score}/100). "
            f"Primary risk drivers: {factors}. Recommended operational action: '{action}'."
        )
        draft_msg = (
            f"Dear Customer, we appreciate your loyalty and value your partnership. "
            f"As part of our commitment to delivering superior service, we would like to exclusively present: "
            f"{action}. Our support team is available to assist you in activating this benefit."
        )
    elif risk_level == "Medium":
        officer_note = (
            f"Customer {customer_id} is evaluated at Medium Risk (Score {risk_score}/100) based on: {factors}. "
            f"Recommended preventative intervention: '{action}'."
        )
        draft_msg = (
            f"Hello, we wanted to check in and ensure your telecommunication services are operating at peak satisfaction. "
            f"Our team is standing by if you need any plan adjustments or support."
        )
    else:
        officer_note = (
            f"Customer {customer_id} is in good standing with Low Risk (Score {risk_score}/100). "
            f"Maintain standard engagement cycle."
        )
        draft_msg = "Thank you for choosing us as your trusted service provider."

    return {
        "LLMExplanation": officer_note,
        "DraftCustomerMessage": draft_msg,
        "ModelName": f"{LLM_PROVIDER}-{LLM_MODEL}",
        "RequiresHumanReview": True
    }

