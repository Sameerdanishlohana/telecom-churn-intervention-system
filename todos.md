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

## [IN PROGRESS] Phase 2: Database Schema & Staging / Lakehouse DDLs (MySQL 8.0)
- [ ] Create database initialization and staging tables DDL (`sql/01_staging_bronze_ddl.sql`)
  - `stg_customers`, `stg_tickets`, `stg_plans`
- [ ] Create Lakehouse / Dimensional Warehouse DDL (`sql/02_silver_gold_warehouse_ddl.sql`)
  - Dimensions: `DimCustomer`, `DimContract`, `DimPayment`, `DimSnapshotDate`
  - Snowflaked Service Dimension: `DimService` -> `DimServiceCategory`
  - Fact Tables: `FactCustomerChurn`, `FactCustomerService`, `FactRetentionAction` (AI write-back)
- [ ] Implement Data Mart Views (`Customer Mart` & `Retention Mart`) & Indexing Strategy (`sql/03_indexes_and_marts.sql`)
  - PKs, unique business keys, FK join indexes, composite filter indexes `(RiskLevel, RecommendedAction)`
  - Formal documentation on R-Tree non-applicability (non-spatial data)

---

## [PENDING] Phase 3: Robust ETL Pipeline (Python + Pandas + SQLAlchemy)
- [ ] Implement `src/etl_pipeline.py`:
  - **Extract**: Ingest CSVs into Staging / Bronze layer with audit logs (`LoadBatchID`, timestamps)
  - **Transform**: Text trimming, standardise Yes/No/binary flags, handle blank `TotalCharges` -> `NULL`/median/numeric casting, duplicate check on `customerID`, derive `ChurnFlag`, `TenureBand`, surrogate keys
  - **Load**: Dimensions first, Facts second with referential integrity; Bronze -> Silver -> Gold
- [ ] Execute ETL pipeline and perform data quality reconciliation (row counts, null audits, FK referential validity)

---

## [PENDING] Phase 4: Exploratory Data Analysis (EDA) & Agent Rule Tuning
- [ ] Complete `notebooks/01_eda_and_rule_tuning.ipynb`
  - Churn breakdown across contract types, tenure bands, monthly charges quartiles, internet services, payment methods, support ticket counts
  - Calibrate and justify heuristic rule point weights based on statistical churn propensity

---

## [PENDING] Phase 5: Intelligent Agent & LLM Intervention Engine
- [ ] Implement perceive-reason-act rule engine in `src/retention_agent.py`
  - Compute `RiskScore` (0–100 capped), assign `RiskLevel` (Low: 0–39, Medium: 40–69, High: 70–100)
  - Decision table mapping risk level and context to actionable retention offers
- [ ] Implement LLM explanation and draft communication module in `src/llm_explainer.py`
  - Strict structured JSON prompt, low temperature, strict grounding on structured facts
  - Deterministic offline fallback template when API key is unconfigured
- [ ] Write-back AI results to `FactRetentionAction` and `Retention Mart`

---

## [PENDING] Phase 6: Power BI Reporting & Final Deliverables
- [ ] Build 4-page Power BI Dashboard:
  1. Executive Overview (KPI cards: total customers, churn rate, monthly revenue at risk)
  2. Customer Segments (Churn rate by contract, tenure, payment, internet service)
  3. Service & Billing (Charge distribution, service adoption, payment options)
  4. Retention Actions (Risk levels, recommended actions, drill-through, LLM explanations)
- [ ] Ensure strict BI guidelines: No fabricated historical trends; rely strictly on snapshot date + LoadBatchID
- [ ] Query plan benchmarking (`EXPLAIN`) before/after index deployment
- [ ] Final project report & repository wrap-up

