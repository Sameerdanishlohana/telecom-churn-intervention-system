-- ============================================================================
-- 02_silver_gold_warehouse_ddl.sql
-- Dimensional Star Schema with Snowflaked Service Dimension
-- FAST NUCES Karachi - DWBI (BDS-5B)
-- Target RDBMS: MySQL 8.0+
-- ============================================================================

USE telecom_churn_dw;

-- Disable FK checks for clean DDL drops
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS FactRetentionAction;
DROP TABLE IF EXISTS FactCustomerService;
DROP TABLE IF EXISTS FactCustomerChurn;
DROP TABLE IF EXISTS DimService;
DROP TABLE IF EXISTS DimServiceCategory;
DROP TABLE IF EXISTS DimSnapshotDate;
DROP TABLE IF EXISTS DimPayment;
DROP TABLE IF EXISTS DimContract;
DROP TABLE IF EXISTS DimCustomer;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- DIMENSION: DimCustomer
-- ----------------------------------------------------------------------------
CREATE TABLE DimCustomer (
    CustomerKey INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID VARCHAR(50) NOT NULL, -- Business Key
    Gender VARCHAR(20),
    SeniorCitizen INT,
    Partner VARCHAR(10),
    Dependents VARCHAR(10),
    CONSTRAINT uq_dimcustomer_businesskey UNIQUE (CustomerID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIMENSION: DimContract
-- ----------------------------------------------------------------------------
CREATE TABLE DimContract (
    ContractKey INT AUTO_INCREMENT PRIMARY KEY,
    ContractType VARCHAR(30) NOT NULL,
    PaperlessBilling VARCHAR(10),
    TenureBand VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIMENSION: DimPayment
-- ----------------------------------------------------------------------------
CREATE TABLE DimPayment (
    PaymentKey INT AUTO_INCREMENT PRIMARY KEY,
    PaymentMethod VARCHAR(50) NOT NULL,
    PaymentType VARCHAR(30), -- Electronic / Mail / Bank / Card
    AutoPayFlag TINYINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIMENSION: DimSnapshotDate (Snapshot-based ETL design)
-- ----------------------------------------------------------------------------
CREATE TABLE DimSnapshotDate (
    SnapshotDateKey INT PRIMARY KEY, -- YYYYMMDD
    SnapshotDate DATE NOT NULL,
    Year INT NOT NULL,
    Month INT NOT NULL,
    Quarter INT NOT NULL,
    LoadBatchID VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- SNOWFLAKE OUTRIGGER: DimServiceCategory
-- ----------------------------------------------------------------------------
CREATE TABLE DimServiceCategory (
    ServiceCategoryKey INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(50) NOT NULL UNIQUE -- Phone, Internet, Security/Support, Streaming
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIMENSION: DimService (Snowflaked to DimServiceCategory)
-- ----------------------------------------------------------------------------
CREATE TABLE DimService (
    ServiceKey INT AUTO_INCREMENT PRIMARY KEY,
    ServiceName VARCHAR(50) NOT NULL,
    ServiceOption VARCHAR(50) NOT NULL,
    ServiceCategoryKey INT NOT NULL,
    CONSTRAINT fk_dimservice_category FOREIGN KEY (ServiceCategoryKey) 
        REFERENCES DimServiceCategory(ServiceCategoryKey)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- FACT TABLE: FactCustomerChurn
-- Grain: One row per customer per warehouse snapshot
-- ----------------------------------------------------------------------------
CREATE TABLE FactCustomerChurn (
    ChurnFactKey BIGINT AUTO_INCREMENT PRIMARY KEY,
    CustomerKey INT NOT NULL,
    ContractKey INT NOT NULL,
    PaymentKey INT NOT NULL,
    SnapshotDateKey INT NOT NULL,
    TenureMonths INT NOT NULL,
    MonthlyCharges DECIMAL(10, 2) NOT NULL,
    TotalCharges DECIMAL(10, 2) NOT NULL,
    ChurnFlag TINYINT NOT NULL, -- 1 = Yes, 0 = No
    RiskScore INT DEFAULT 0,
    CONSTRAINT fk_churn_customer FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
    CONSTRAINT fk_churn_contract FOREIGN KEY (ContractKey) REFERENCES DimContract(ContractKey),
    CONSTRAINT fk_churn_payment FOREIGN KEY (PaymentKey) REFERENCES DimPayment(PaymentKey),
    CONSTRAINT fk_churn_date FOREIGN KEY (SnapshotDateKey) REFERENCES DimSnapshotDate(SnapshotDateKey)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- FACT TABLE: FactCustomerService
-- Grain: One row per customer, subscribed service, and snapshot
-- ----------------------------------------------------------------------------
CREATE TABLE FactCustomerService (
    ServiceFactKey BIGINT AUTO_INCREMENT PRIMARY KEY,
    CustomerKey INT NOT NULL,
    ServiceKey INT NOT NULL,
    SnapshotDateKey INT NOT NULL,
    ActiveFlag TINYINT NOT NULL,
    CONSTRAINT fk_servicefact_customer FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
    CONSTRAINT fk_servicefact_service FOREIGN KEY (ServiceKey) REFERENCES DimService(ServiceKey),
    CONSTRAINT fk_servicefact_date FOREIGN KEY (SnapshotDateKey) REFERENCES DimSnapshotDate(SnapshotDateKey)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- FACT TABLE: FactRetentionAction (AI Agent & LLM Write-Back Table)
-- Grain: One row per customer evaluation per agent execution run
-- ----------------------------------------------------------------------------
CREATE TABLE FactRetentionAction (
    ActionKey BIGINT AUTO_INCREMENT PRIMARY KEY,
    CustomerKey INT NOT NULL,
    RiskScore INT NOT NULL,
    RiskLevel VARCHAR(20) NOT NULL, -- Low, Medium, High
    RecommendedAction VARCHAR(255) NOT NULL,
    LLMExplanation TEXT,
    DraftCustomerMessage TEXT,
    RuleVersion VARCHAR(50) NOT NULL,
    RunDate DATE NOT NULL,
    ModelName VARCHAR(100) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_retention_customer FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

