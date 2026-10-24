"""SQLAlchemy connection helper for the MySQL-backed AI service."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.getenv("AVATAR_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "AVATAR_DATABASE_URL tanımlı değil. .env.example dosyasını .env olarak kopyalayıp MySQL bağlantısını ayarlayın."
        )
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=5, max_overflow=5)
