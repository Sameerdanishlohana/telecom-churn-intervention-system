-- ============================================================================
-- 03_indexes_and_marts.sql
-- Indexes, Data Mart Views, and EXPLAIN Benchmark Queries
-- FAST NUCES Karachi - DWBI (BDS-5B)
-- Target RDBMS: MySQL 8.0+
-- ============================================================================

USE telecom_churn_dw;

-- ============================================================================
-- SECTION A: INDEXING STRATEGY
-- ============================================================================

-- 1. Foreign Key / Join Indexes
CREATE INDEX idx_fk_churn_customer ON FactCustomerChurn(CustomerKey);
CREATE INDEX idx_fk_churn_contract ON FactCustomerChurn(ContractKey);
CREATE INDEX idx_fk_churn_payment ON FactCustomerChurn(PaymentKey);
CREATE INDEX idx_fk_churn_date ON FactCustomerChurn(SnapshotDateKey);

CREATE INDEX idx_fk_custservice_customer ON FactCustomerService(CustomerKey);
CREATE INDEX idx_fk_custservice_service ON FactCustomerService(ServiceKey);

CREATE INDEX idx_fk_retention_customer ON FactRetentionAction(CustomerKey);
CREATE INDEX idx_retention_rundate ON FactRetentionAction(RunDate);

-- 2. Frequently Filtered / Slicer Indexes
CREATE INDEX idx_churn_flag ON FactCustomerChurn(ChurnFlag);
CREATE INDEX idx_contract_type ON DimContract(ContractType);
CREATE INDEX idx_payment_method ON DimPayment(PaymentMethod);

-- 3. Composite Index for Retention Operations
CREATE INDEX idx_retention_risk_action ON FactRetentionAction(RiskLevel, RecommendedAction);

-- ============================================================================
-- SECTION B: R-TREE SPATIAL INDEXING NON-APPLICABILITY NOTE
-- ============================================================================
/*
  DOCUMENTATION NOTE (Academic Requirement):
  The Telco Customer Churn dataset and associated synthetic tables contain no 
  spatial coordinates (Latitude, Longitude) or GIS Geometry datatypes. 
  Therefore, an R-Tree spatial index is intentionally NOT applicable. 
  Artificial coordinates were deliberately omitted in accordance with the 
  project proposal to maintain data integrity and avoid fabricated geography.
*/

-- ============================================================================
-- SECTION C: DATA MART VIEWS
-- ============================================================================

-- Data Mart 1: Customer Mart (Comprehensive profile, contract, billing, churn)
CREATE OR REPLACE VIEW vw_CustomerMart AS
SELECT 
    c.CustomerKey,
    c.CustomerID,
    c.Gender,
    c.SeniorCitizen,
    c.Partner,
    c.Dependents,
    co.ContractType,
    co.PaperlessBilling,
    co.TenureBand,
    p.PaymentMethod,
    p.PaymentType,
    p.AutoPayFlag,
    d.SnapshotDate,
    f.TenureMonths,
    f.MonthlyCharges,
    f.TotalCharges,
    f.ChurnFlag,
    f.RiskScore
FROM FactCustomerChurn f
JOIN DimCustomer c ON f.CustomerKey = c.CustomerKey
JOIN DimContract co ON f.ContractKey = co.ContractKey
JOIN DimPayment p ON f.PaymentKey = p.PaymentKey
JOIN DimSnapshotDate d ON f.SnapshotDateKey = d.SnapshotDateKey;

-- Data Mart 2: Retention Mart (Risk scores, interventions, LLM explanations)
CREATE OR REPLACE VIEW vw_RetentionMart AS
SELECT 
    r.ActionKey,
    c.CustomerID,
    c.Gender,
    co.ContractType,
    co.TenureBand,
    f.MonthlyCharges,
    f.ChurnFlag,
    r.RiskScore,
    r.RiskLevel,
    r.RecommendedAction,
    r.LLMExplanation,
    r.DraftCustomerMessage,
    r.RuleVersion,
    r.RunDate,
    r.ModelName
FROM FactRetentionAction r
JOIN DimCustomer c ON r.CustomerKey = c.CustomerKey
LEFT JOIN FactCustomerChurn f ON c.CustomerKey = f.CustomerKey
LEFT JOIN DimContract co ON f.ContractKey = co.ContractKey;

-- ============================================================================
-- SECTION D: EXPLAIN BENCHMARK TEST QUERIES
-- ============================================================================
-- Run these queries before and after adding indexes to record execution plans in reports:
-- EXPLAIN SELECT RiskLevel, RecommendedAction, COUNT(*) FROM FactRetentionAction GROUP BY RiskLevel, RecommendedAction;
-- EXPLAIN SELECT c.CustomerID, f.MonthlyCharges, f.ChurnFlag FROM FactCustomerChurn f JOIN DimCustomer c ON f.CustomerKey = c.CustomerKey WHERE f.ChurnFlag = 1;

