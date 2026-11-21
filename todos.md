# Telecom Churn Intervention System - Project Phase Roadmap

**Academic Context:** FAST NUCES Karachi, Data Warehousing & Business Intelligence (BDS-5B)  
**Team:** Sameer Danish (24K-2504, Lead), Muhammad Arham Arshad (24K-2529), Hadeer Abbas (24K-2503)

---

## [DONE] Phase 1: Environment Setup, Data Sourcing & Synthetic Data Generation
- [x] Create project directory structure (`data/`, `sql/`, `src/`, `notebooks/`, documentation)
- [x] Initialize configuration & environment template (`src/config.py`, `.env.example`, `requirements.txt`)
- [x] Source primary dataset: `Telco-Customer-Churn.csv` (Verified: 7,043 rows, 21 columns) in `data/raw/`
- [x] Implement synthetic data generator script: `src/generate_synthetic_data.py`
  - Synthetic customer support ticket log (`synthetic_support_tickets.csv`: 4,546 records matched to actual customer IDs)
  - Synthetic plan/tariff & retention-offer reference table (`synthetic_plans_tariffs.csv`: 8 service tariff plans)
- [x] Verify dataset shape, column names, null counts, and confirm files in `data/raw/`

---

## [DONE] Phase 2: Database Schema & Staging / Lakehouse DDLs (MySQL 8.0)
- [x] Create database initialization and staging tables DDL (`sql/01_staging_bronze_ddl.sql`)
  - `stg_customers`, `stg_tickets`, `stg_plans`
- [x] Create Lakehouse / Dimensional Warehouse DDL (`sql/02_silver_gold_warehouse_ddl.sql`)
  - Dimensions: `DimCustomer`, `DimContract`, `DimPayment`, `DimSnapshotDate`
  - Snowflaked Service Dimension: `DimService` -> `DimServiceCategory`
  - Fact Tables: `FactCustomerChurn`, `FactCustomerService`, `FactRetentionAction` (AI write-back)
- [x] Implement Data Mart Views (`Customer Mart` & `Retention Mart`) & Indexing Strategy (`sql/03_indexes_and_marts.sql`)
  - PKs, unique business keys, FK join indexes, composite filter indexes `(RiskLevel, RecommendedAction)`
  - Formal documentation on R-Tree non-applicability (non-spatial data)
- [x] Verified creation of all 12 warehouse tables and 2 views in local MySQL 8.0.46 instance.

---

## [DONE] Phase 3: Robust ETL Pipeline (Python + Pandas + SQLAlchemy)
- [x] Implement `src/etl_pipeline.py`:
  - **Extract**: Ingest CSVs into Staging / Bronze layer with audit logs (`LoadBatchID`, timestamps)
  - **Transform**: Text trimming, standardise Yes/No/binary flags, handle blank `TotalCharges` -> `0.00` with audit, duplicate check on `customerID`, derive `ChurnFlag`, `TenureBand`, surrogate keys
  - **Load**: Dimensions first, Facts second with referential integrity; Bronze -> Silver -> Gold
- [x] Execute ETL pipeline and perform data quality reconciliation:
  - Staging Customers: 7,043 | DimCustomer: 7,043 | FactCustomerChurn: 7,043 (100% matched)
  - FactCustomerService bridge: 70,430 rows (10 services $\times$ 7,043 customers)
  - Verified Customer Mart View: 7,043 records, $456,116.60 monthly revenue ($139,130.85 churned, 26.54% churn rate)

---

## [DONE] Phase 4: Exploratory Data Analysis (EDA) & Agent Rule Tuning
- [x] Complete churn distribution and risk driver analysis:
  - Contract type impact: Month-to-month = **42.71%** churn vs Two-year = **2.83%** churn
  - Tenure band impact: 0-12 Months = **47.44%** churn vs 49+ Months = **9.51%** churn
  - Payment method impact: Electronic check = **45.29%** churn vs AutoPay = **~15.9%** churn
  - Support ticket impact: Multi-ticket frequency correlation observed and calibrated
- [x] Heuristic point weights validated and aligned with statistical propensity

---

## [DONE] Phase 5: Intelligent Agent & LLM Intervention Engine
- [x] Implement perceive-reason-act rule engine in `src/retention_agent.py` and `src/run_agent.py`
  - Computed `RiskScore` (0–100 capped), assigned `RiskLevel` (Low: 0–39, Medium: 40–69, High: 70–100)
  - Evaluated 7,043 customers:
    - **High Risk:** 81 customers (**83.95% actual churn rate**, $6,728.05 monthly revenue at stake)
    - **Medium Risk:** 2,429 customers (**50.39% actual churn rate**, $198,508.05 monthly revenue at stake)
    - **Low Risk:** 4,533 customers (**12.73% actual churn rate**, $250,880.50 monthly revenue)
- [x] Implement LLM explanation and draft communication module in `src/llm_explainer.py`
  - Generated human-in-the-loop notes and customized draft messages grounded strictly in structured fields
- [x] Executed full write-back into `FactRetentionAction` and synchronized `FactCustomerChurn.RiskScore`
- [x] Benchmarked MySQL query plans with `EXPLAIN` (Verified composite index `idx_retention_risk_action` running `Using index`)

---

## [IN PROGRESS] Phase 6: Power BI Reporting & Final Deliverables
- [ ] Build 4-page Power BI Dashboard:
  1. Executive Overview (KPI cards: total customers, churn rate, monthly revenue at risk)
  2. Customer Segments (Churn rate by contract, tenure, payment, internet service)
  3. Service & Billing (Charge distribution, service adoption, payment options)
  4. Retention Actions (Risk levels, recommended actions, drill-through, LLM explanations)
- [ ] Ensure strict BI guidelines: No fabricated historical trends; rely strictly on snapshot date + LoadBatchID
- [ ] Query plan benchmarking (`EXPLAIN`) before/after index deployment
- [ ] Final project report & repository wrap-up

