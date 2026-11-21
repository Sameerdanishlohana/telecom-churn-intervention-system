-- ============================================================================
-- 01_staging_bronze_ddl.sql
-- Telecom Churn Intervention System
-- FAST NUCES Karachi - DWBI (BDS-5B)
-- Target RDBMS: MySQL 8.0+
-- ============================================================================

CREATE DATABASE IF NOT EXISTS telecom_churn_dw;
USE telecom_churn_dw;

-- Drop Staging Tables if re-running
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_tickets;
DROP TABLE IF EXISTS stg_plans;

-- ----------------------------------------------------------------------------
-- 1. Staging Customers (Direct 1:1 ingest from Telco-Customer-Churn.csv)
-- ----------------------------------------------------------------------------
CREATE TABLE stg_customers (
    customerID VARCHAR(50) NOT NULL,
    gender VARCHAR(20),
    SeniorCitizen INT,
    Partner VARCHAR(10),
    Dependents VARCHAR(10),
    tenure INT,
    PhoneService VARCHAR(10),
    MultipleLines VARCHAR(30),
    InternetService VARCHAR(30),
    OnlineSecurity VARCHAR(30),
    OnlineBackup VARCHAR(30),
    DeviceProtection VARCHAR(30),
    TechSupport VARCHAR(30),
    StreamingTV VARCHAR(30),
    StreamingMovies VARCHAR(30),
    Contract VARCHAR(30),
    PaperlessBilling VARCHAR(10),
    PaymentMethod VARCHAR(50),
    MonthlyCharges DECIMAL(10, 2),
    TotalCharges VARCHAR(50), -- Kept as VARCHAR in staging to capture raw whitespace/nulls
    Churn VARCHAR(10),
    LoadBatchID VARCHAR(50),
    IngestionTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- 2. Staging Support Tickets (Synthetic Customer Support Log)
-- ----------------------------------------------------------------------------
CREATE TABLE stg_tickets (
    TicketID VARCHAR(50) NOT NULL,
    CustomerID VARCHAR(50) NOT NULL,
    TicketDate DATE,
    Category VARCHAR(100),
    Priority VARCHAR(20),
    Status VARCHAR(20),
    ResolutionDays INT NULL,
    IsSynthetic TINYINT DEFAULT 1,
    LoadBatchID VARCHAR(50),
    IngestionTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- 3. Staging Plans & Tariffs (Synthetic Tariff and Retention Offer Reference)
-- ----------------------------------------------------------------------------
CREATE TABLE stg_plans (
    PlanID VARCHAR(50) NOT NULL,
    PlanName VARCHAR(100),
    ServiceCategory VARCHAR(50),
    BaseMonthlyRate DECIMAL(10, 2),
    ContractDiscount1Yr DECIMAL(5, 2),
    ContractDiscount2Yr DECIMAL(5, 2),
    EligibleRetentionOffer VARCHAR(255),
    LoadBatchID VARCHAR(50),
    IngestionTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

