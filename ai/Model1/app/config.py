import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path(os.getenv("MODEL_DIR", ROOT / "models"))
if not MODEL_DIR.is_absolute():
    MODEL_DIR = ROOT / MODEL_DIR
AI_ROOT = ROOT.parent
MODEL_B_DIR = Path(os.getenv("MODEL_B_DIR", AI_ROOT / "Model2" / "models"))
if not MODEL_B_DIR.is_absolute():
    MODEL_B_DIR = ROOT / MODEL_B_DIR
API_KEY = os.getenv("API_KEY", "")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

MODEL_B_AUDIT_DB = Path(os.getenv('MODEL_B_AUDIT_DB', AI_ROOT / 'Model2' / 'var' / 'model_b_audit.sqlite3'))
if not MODEL_B_AUDIT_DB.is_absolute():
    MODEL_B_AUDIT_DB = ROOT / MODEL_B_AUDIT_DB
