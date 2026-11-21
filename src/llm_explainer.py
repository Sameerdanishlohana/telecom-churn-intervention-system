"""
LLM Explanation and Draft Communication Module.
Integrated with OpenRouter API (DeepSeek/other models) with strict safeguards:
- Grounded solely on structured input attributes
- Temperature set low (0.2)
- Structured JSON output format
- Automatic fallback to deterministic template generator if API is unreachable or times out
"""

import os
import sys
import json
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL

OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY", "") or LLM_API_KEY


def generate_llm_explanation(decision_record: dict) -> dict:
    """
    Receives structured agent output and produces:
    1. Short retention-officer explanation
    2. Draft polite retention message
    Safeguards: Grounded strictly on supplied fields, low temperature, fallback capable.
    """
    customer_id = decision_record.get("CustomerID", "Valued Customer")
    risk_level = decision_record.get("RiskLevel", "Low")
    risk_score = decision_record.get("RiskScore", 0)
    action = decision_record.get("RecommendedAction", "Routine loyalty communication")
    factors = decision_record.get("ContributingFactors", "Standard usage patterns")

    # If OpenRouter key is available, call the live LLM
    if OPEN_ROUTER_KEY and OPEN_ROUTER_KEY.startswith("sk-or-"):
        try:
            prompt = f"""
You are an AI assistant for a Telecommunications Retention Team.
Strict Safeguards:
- Base your output ONLY on the structured customer data provided below.
- Do NOT fabricate discounts or terms not mentioned in RecommendedAction.
- Output MUST be valid JSON with exactly two string keys: "LLMExplanation" and "DraftCustomerMessage".

Customer Data:
- Customer ID: {customer_id}
- Churn Risk Score: {risk_score}/100
- Risk Level: {risk_level}
- Contributing Risk Factors: {factors}
- Recommended Retention Action: {action}

JSON format required:
{{
  "LLMExplanation": "<Concise 1-2 sentence note for the retention officer explaining the decision>",
  "DraftCustomerMessage": "<Polite, personalized 2-sentence message to the customer offering the recommended action>"
}}
"""
            headers = {
                "Authorization": f"Bearer {OPEN_ROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Sameerdanishlohana/telecom-churn-intervention-system",
                "X-Title": "Telecom Churn Intervention System"
            }
            payload = {
                "model": LLM_MODEL if LLM_MODEL else "deepseek/deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a specialized telecom customer retention reasoning engine. Always respond strictly in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 250
            }

            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                raw_text = resp.json()["choices"][0]["message"]["content"].strip()
                # Clean Markdown backticks if returned
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                    raw_text = raw_text.strip()
                data = json.loads(raw_text)
                return {
                    "LLMExplanation": data.get("LLMExplanation", "").strip(),
                    "DraftCustomerMessage": data.get("DraftCustomerMessage", "").strip(),
                    "ModelName": f"OpenRouter/{LLM_MODEL}",
                    "RequiresHumanReview": True
                }
        except Exception:
            # Silently fall through to deterministic template fallback if API fails
            pass

    # Deterministic fallback generator (Offline / Default fallback)
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
        "ModelName": f"Fallback-Rules/{LLM_MODEL}",
        "RequiresHumanReview": True
    }
