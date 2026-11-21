# Power BI DAX Measures & Page Specification Guide
**Project:** Telecom Churn Intervention System  
**Team:** Sameer Danish (24K-2504), Muhammad Arham Arshad (24K-2529), Hadeer Abbas (24K-2503)  
**Database Connection:** MySQL 8.0 `telecom_churn_dw` (DirectQuery or Import from `vw_CustomerMart` and `vw_RetentionMart`, or the underlying Fact/Dim tables)

---

## 1. Key DAX Measures

Paste these measures into your Model in Power BI Desktop:

### Core KPIs
```dax
Total Customers = COUNTROWS(DimCustomer)
```

```dax
Churned Customers = 
CALCULATE(
    COUNTROWS(FactCustomerChurn),
    FactCustomerChurn[ChurnFlag] = 1
)
```

```dax
Churn Rate = 
DIVIDE(
    [Churned Customers],
    [Total Customers],
    0
)
```

```dax
Total Monthly Revenue = 
SUM(FactCustomerChurn[MonthlyCharges])
```

```dax
Revenue at Churn Risk = 
CALCULATE(
    SUM(FactCustomerChurn[MonthlyCharges]),
    FactCustomerChurn[ChurnFlag] = 1
)
```

```dax
High Risk Customer Count = 
CALCULATE(
    COUNTROWS(FactRetentionAction),
    FactRetentionAction[RiskLevel] = "High"
)
```

```dax
High Risk Revenue at Stake = 
CALCULATE(
    SUM(FactCustomerChurn[MonthlyCharges]),
    FactRetentionAction[RiskLevel] = "High"
)
```

---

## 2. 4-Page Dashboard Layout & Visual Guide

### Page 1: Executive Overview
* **Top KPI Cards:**
  1. `Total Customers` (7,043)
  2. `Churn Rate` (26.54%)
  3. `Total Monthly Revenue` ($456.12K)
  4. `Monthly Revenue Lost to Churn` ($139.13K)
  5. `High Risk Customers Identified` (81)
* **Visuals:**
  - **Donut Chart:** Churn vs Active Breakdown
  - **Bar Chart:** Monthly Revenue by Contract Type (Month-to-month, One year, Two year)
  - **Bar Chart:** Churn Rate by Contract Type
* **Slicers:** Snapshot Date, Contract Type, AutoPay Flag

### Page 2: Customer Segments
* **Visuals:**
  - **Clustered Bar Chart:** Churn Rate by `TenureBand` (0-12, 13-24, 25-48, 49+ Months)
  - **Clustered Bar Chart:** Churn Rate by `PaymentMethod` (Electronic Check, Mailed Check, Bank Transfer, Credit Card)
  - **100% Stacked Bar Chart:** Churn Distribution across Demographic Segments (SeniorCitizen, Partner, Dependents)
* **Slicers:** Tenure Band, Senior Citizen (0/1), Dependents (Yes/No)

### Page 3: Service & Billing Analysis
* **Visuals:**
  - **Histogram / Binned Column Chart:** Monthly Charges Distribution ($20 - $120)
  - **Matrix / Heatmap:** Churn Rate across Internet Service Options (DSL, Fiber Optic, No Internet) vs Additional Protection Services (OnlineSecurity, TechSupport)
  - **Detailed Customer Table:** CustomerID, Tenure, Monthly Charges, Total Charges, Churn Status
* **Slicers:** Internet Service, Payment Type, Paperless Billing

### Page 4: Retention Actions (AI Intervention & Write-Back)
* **Visuals:**
  - **Donut Chart / Funnel:** Customers by `RiskLevel` (Low: 4,533 | Medium: 2,429 | High: 81)
  - **Horizontal Bar Chart:** Recommended Actions Breakdown
  - **Scatter / Bubble Plot:** `RiskScore` vs `MonthlyCharges` (color-coded by `RiskLevel`)
  - **Detail & Drill-Through Card / Table:**
    - Columns: `CustomerID`, `RiskScore`, `RiskLevel`, `RecommendedAction`, `LLMExplanation`, `DraftCustomerMessage`
* **Slicers:** Risk Level (High, Medium, Low), Recommended Action
* **Drill-Through Target:** Enable drill-through on `RiskLevel` from Page 1 and Page 2 straight to this customer list!

---

## 3. Strict Academic BI Compliance Checklist
- [x] **No Historical Trend Implication:** All charts are cross-sectional snapshots tied to `SnapshotDate` (`2026-11-21`) and `LoadBatchID`.
- [x] **Surrogate & Business Keys:** Slicers and tables display `CustomerID` (business key) while relationships join on surrogate integer keys.
- [x] **Verified Metric Match:** Churn rate strictly equals 26.54%, Total Monthly Revenue matches $456,116.60.

