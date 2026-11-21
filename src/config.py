"""
Configuration module for the Telecom Churn Intervention System.
Loads environment variables and sets path constants and database connection settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
BRONZE_DATA_DIR = DATA_DIR / "bronze"
SILVER_DATA_DIR = DATA_DIR / "silver"
GOLD_DATA_DIR = DATA_DIR / "gold"
SQL_DIR = BASE_DIR / "sql"

# Ensure runtime directories exist
for path in [RAW_DATA_DIR, BRONZE_DATA_DIR, SILVER_DATA_DIR, GOLD_DATA_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Database Connection Variables
DB_TYPE = os.getenv("DB_TYPE", "mysql")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "telecom_churn_dw")

# Snapshot & Audit Parameters
ETL_SNAPSHOT_DATE = os.getenv("ETL_SNAPSHOT_DATE", "2026-11-21")
LOAD_BATCH_ID = os.getenv("LOAD_BATCH_ID", "BATCH_20261121_01")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "offline_fallback")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "fallback-rules-v1")


def get_db_url() -> str:
    """Constructs the SQLAlchemy database URL based on environment settings."""
    if DB_TYPE.lower() == "mysql":
        return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    elif DB_TYPE.lower() in ["postgres", "postgresql"]:
        return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Default SQLite fallback for local testing if MySQL is not immediately reachable
        sqlite_path = BASE_DIR / f"{DB_NAME}.db"
        return f"sqlite:///{sqlite_path}"

