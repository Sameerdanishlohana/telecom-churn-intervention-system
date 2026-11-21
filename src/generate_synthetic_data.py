"""
Synthetic Data Generator for the Telecom Churn Intervention System.
FAST NUCES Karachi - DWBI (BDS-5B)

Generates supporting sources marked strictly as synthetic:
1. synthetic_support_tickets.csv (Customer Support Ticket Log)
2. synthetic_plans_tariffs.csv (Plan/Tariff & Retention Offer Reference Sheet)
"""

import random
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
from config import RAW_DATA_DIR, ETL_SNAPSHOT_DATE

# Set deterministic random seed for academic reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)


def generate_support_tickets(customer_ids, filename="synthetic_support_tickets.csv"):
    """
    Generates a realistic support ticket log for a subset of customers.
    Fields: TicketID, CustomerID, TicketDate, Category, Priority, Status, ResolutionDays
    """
    categories = ["Billing Inquiry", "Technical Support", "Network Outage", "Service Cancellation Request", "Speed & Connectivity"]
    priorities = ["Low", "Medium", "High", "Critical"]
    statuses = ["Resolved", "Closed", "Pending", "Escalated"]
    
    # Weight distributions
    cat_weights = [0.35, 0.25, 0.15, 0.10, 0.15]
    prio_weights = [0.30, 0.40, 0.20, 0.10]
    status_weights = [0.70, 0.20, 0.07, 0.03]
    
    snapshot_dt = datetime.strptime(ETL_SNAPSHOT_DATE, "%Y-%m-%d")
    
    records = []
    ticket_counter = 10001
    
    # Approximately 40% of customers have filed tickets, some multiple times
    for cid in customer_ids:
        # Probabilistic ticket count: 60% 0 tickets, 25% 1 ticket, 10% 2 tickets, 5% 3-5 tickets
        roll = random.random()
        if roll < 0.60:
            ticket_count = 0
        elif roll < 0.85:
            ticket_count = 1
        elif roll < 0.95:
            ticket_count = 2
        else:
            ticket_count = random.randint(3, 5)
            
        for _ in range(ticket_count):
            # Tickets occurred within the last 90 days before snapshot
            days_ago = random.randint(1, 90)
            ticket_date = (snapshot_dt - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            category = random.choices(categories, weights=cat_weights)[0]
            priority = random.choices(priorities, weights=prio_weights)[0]
            status = random.choices(statuses, weights=status_weights)[0]
            
            if status in ["Resolved", "Closed"]:
                res_days = random.randint(1, 10)
            else:
                res_days = None  # Still open
                
            records.append({
                "TicketID": f"TCK-{ticket_counter}",
                "CustomerID": cid,
                "TicketDate": ticket_date,
                "Category": category,
                "Priority": priority,
                "Status": status,
                "ResolutionDays": res_days,
                "IsSynthetic": 1
            })
            ticket_counter += 1
            
    df_tickets = pd.DataFrame(records)
    out_path = RAW_DATA_DIR / filename
    df_tickets.to_csv(out_path, index=False)
    print(f"[+] Successfully generated {len(df_tickets)} synthetic support tickets at: {out_path}")
    return df_tickets


def generate_plans_and_tariffs(filename="synthetic_plans_tariffs.csv"):
    """
    Generates reference table for internet & phone plans, discounts, and retention offers.
    Fields: PlanID, PlanName, ServiceCategory, BaseMonthlyRate, ContractDiscount1Yr, ContractDiscount2Yr, EligibleRetentionOffer
    """
    plans = [
        {
            "PlanID": "PLN-DSL-01",
            "PlanName": "DSL Basic Connection",
            "ServiceCategory": "Internet",
            "BaseMonthlyRate": 29.99,
            "ContractDiscount1Yr": 0.05,
            "ContractDiscount2Yr": 0.10,
            "EligibleRetentionOffer": "Free Speed Upgrade for 6 Months"
        },
        {
            "PlanID": "PLN-DSL-02",
            "PlanName": "DSL Turbo Speed",
            "ServiceCategory": "Internet",
            "BaseMonthlyRate": 44.99,
            "ContractDiscount1Yr": 0.08,
            "ContractDiscount2Yr": 0.15,
            "EligibleRetentionOffer": "15% Monthly Discount on 12-Month Contract"
        },
        {
            "PlanID": "PLN-FO-01",
            "PlanName": "Fiber Optic Standard",
            "ServiceCategory": "Internet",
            "BaseMonthlyRate": 70.00,
            "ContractDiscount1Yr": 0.10,
            "ContractDiscount2Yr": 0.20,
            "EligibleRetentionOffer": "Offer a discounted 12- or 24-month contract"
        },
        {
            "PlanID": "PLN-FO-02",
            "PlanName": "Fiber Optic Premium Ultra",
            "ServiceCategory": "Internet",
            "BaseMonthlyRate": 99.99,
            "ContractDiscount1Yr": 0.12,
            "ContractDiscount2Yr": 0.22,
            "EligibleRetentionOffer": "Offer a discounted 12- or 24-month contract & Autopay Waiver"
        },
        {
            "PlanID": "PLN-PH-01",
            "PlanName": "Single Line Phone Service",
            "ServiceCategory": "Phone",
            "BaseMonthlyRate": 20.00,
            "ContractDiscount1Yr": 0.05,
            "ContractDiscount2Yr": 0.10,
            "EligibleRetentionOffer": "Free Unlimited International Calling Pack for 3 Months"
        },
        {
            "PlanID": "PLN-PH-02",
            "PlanName": "Multi-Line Phone Family Pack",
            "ServiceCategory": "Phone",
            "BaseMonthlyRate": 35.00,
            "ContractDiscount1Yr": 0.08,
            "ContractDiscount2Yr": 0.15,
            "EligibleRetentionOffer": "Family Line Add-on Discount"
        },
        {
            "PlanID": "PLN-SEC-01",
            "PlanName": "Cyber & Tech Support Essential",
            "ServiceCategory": "Security/Support",
            "BaseMonthlyRate": 15.00,
            "ContractDiscount1Yr": 0.10,
            "ContractDiscount2Yr": 0.20,
            "EligibleRetentionOffer": "Offer a free 3-month TechSupport / OnlineSecurity bundle"
        },
        {
            "PlanID": "PLN-STR-01",
            "PlanName": "All-Access Streaming Bundle",
            "ServiceCategory": "Streaming",
            "BaseMonthlyRate": 25.00,
            "ContractDiscount1Yr": 0.10,
            "ContractDiscount2Yr": 0.18,
            "EligibleRetentionOffer": "Free Streaming Pass for 2 Months"
        }
    ]
    
    df_plans = pd.DataFrame(plans)
    out_path = RAW_DATA_DIR / filename
    df_plans.to_csv(out_path, index=False)
    print(f"[+] Successfully generated {len(df_plans)} synthetic tariff plans at: {out_path}")
    return df_plans


if __name__ == "__main__":
    # Check if primary dataset is available to draw real customer IDs
    primary_csv = RAW_DATA_DIR / "Telco-Customer-Churn.csv"
    if primary_csv.exists():
        df_primary = pd.read_csv(primary_csv)
        customer_ids = df_primary["customerID"].dropna().unique().tolist()
        print(f"[*] Found primary dataset with {len(customer_ids)} customers.")
    else:
        print("[!] Note: Primary 'Telco-Customer-Churn.csv' not yet in data/raw/. Generating with sample customer pool.")
        customer_ids = [f"CUST-{i:05d}" for i in range(1, 7044)]
        
    generate_support_tickets(customer_ids)
    generate_plans_and_tariffs()

