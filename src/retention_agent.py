"""
Intelligent Agent (Perceive-Reason-Act) for Telecom Churn Intervention System.
Evaluates customer profiles from Gold / Customer Mart, computes RiskScore (0-100),
assigns RiskLevel, and selects recommended retention actions via decision table.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))
from config import GOLD_DATA_DIR

RULE_VERSION = "v1.0-proposal-baseline"


class RetentionAgent:
    """
    Goal-based Utility Agent:
    - Perceive: Customer contract, tenure, payment method, support tickets, services
    - Reason: Weighted rule-scoring engine (0-100) + Decision Table
    - Act: Produce structured decision record for write-back
    """
    def __init__(self, rule_version=RULE_VERSION):
        self.rule_version = rule_version

    def evaluate_customer(self, row: dict, ticket_count: int = 0) -> dict:
        score = 0
        reasons = []

        # Rule 1: Contract Type (+25)
        if str(row.get("Contract", "")).lower() == "month-to-month":
            score += 25
            reasons.append("Month-to-month contract (+25)")

        # Rule 2: Tenure <= 12 (+20), 13-24 (+10)
        tenure = float(row.get("tenure", row.get("TenureMonths", 0)))
        if tenure <= 12:
            score += 20
            reasons.append("New customer with tenure <= 12 months (+20)")
        elif tenure <= 24:
            score += 10
            reasons.append("Tenure between 13-24 months (+10)")

        # Rule 3: Electronic Check (+10)
        if "electronic check" in str(row.get("PaymentMethod", "")).lower():
            score += 10
            reasons.append("Manual payment via Electronic Check (+10)")

        # Rule 4: Fiber Optic (+10)
        if "fiber optic" in str(row.get("InternetService", "")).lower():
            score += 10
            reasons.append("High churn propensity Fiber Optic plan (+10)")

        # Rule 5: Internet customer without OnlineSecurity or TechSupport (+10)
        has_internet = str(row.get("InternetService", "")).lower() not in ["no", "none", "nan", ""]
        sec = str(row.get("OnlineSecurity", "")).lower()
        tech = str(row.get("TechSupport", "")).lower()
        if has_internet and (sec == "no" or tech == "no"):
            score += 10
            reasons.append("Missing OnlineSecurity or TechSupport protection (+10)")

        # Rule 6: High Monthly Charges (top quartile approx > 70) (+10)
        monthly_charges = float(row.get("MonthlyCharges", 0))
        if monthly_charges >= 70.0:
            score += 10
            reasons.append("High monthly bill >= $70 (+10)")

        # Rule 7: Two or more support tickets (+10)
        if ticket_count >= 2:
            score += 10
            reasons.append(f"Recurring support complaints ({ticket_count} tickets) (+10)")

        # Cap at 100
        score = min(score, 100)

        # Risk Level categorization
        if score >= 70:
            risk_level = "High"
        elif score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Decision Table for Action Recommendation
        if risk_level == "High":
            if str(row.get("Contract", "")).lower() == "month-to-month":
                action = "Offer a discounted 12- or 24-month contract"
            elif has_internet and (sec == "no" or tech == "no"):
                action = "Offer a free 3-month TechSupport / OnlineSecurity bundle"
            elif "electronic check" in str(row.get("PaymentMethod", "")).lower():
                action = "Offer an autopay incentive and billing assistance"
            else:
                action = "Dedicated Retention Specialist Intervention Call"
        elif risk_level == "Medium":
            action = "Proactive service check-in call or SMS"
        else:
            action = "No action; routine loyalty communication"

        return {
            "CustomerID": row.get("customerID") or row.get("CustomerID"),
            "RiskScore": score,
            "RiskLevel": risk_level,
            "RecommendedAction": action,
            "ContributingFactors": "; ".join(reasons),
            "RuleVersion": self.rule_version
        }

