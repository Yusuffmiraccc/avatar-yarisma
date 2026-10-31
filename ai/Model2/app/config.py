from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODEL_B_DIR = Path(os.getenv("MODEL_B_DIR", ROOT / "models"))
if not MODEL_B_DIR.is_absolute():
    MODEL_B_DIR = ROOT / MODEL_B_DIR

MODEL_B_AUDIT_DB = Path(os.getenv("MODEL_B_AUDIT_DB", ROOT / "var" / "model_b_audit.sqlite3"))
if not MODEL_B_AUDIT_DB.is_absolute():
    MODEL_B_AUDIT_DB = ROOT / MODEL_B_AUDIT_DB

MODEL_B_AUDIT_MIGRATION = Path(
    os.getenv("MODEL_B_AUDIT_MIGRATION", ROOT / "sql" / "001_model_b_audit.sql")
)
if not MODEL_B_AUDIT_MIGRATION.is_absolute():
    MODEL_B_AUDIT_MIGRATION = ROOT / MODEL_B_AUDIT_MIGRATION

API_KEY = os.getenv("API_KEY", "")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
