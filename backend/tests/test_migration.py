"""Migration smoke + şema parity: boş MySQL'e upgrade, ORM metadata ile fark yok, downgrade/upgrade döngüsü."""
import os
import subprocess
import sys

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from tests.conftest import ROOT_URL

MIG_DB = "avatar_migtest"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alembic(url: str, *args: str):
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True
    )


def test_migration_matches_orm_metadata_and_roundtrips():
    import app.models  # noqa: F401
    from app.db.base import Base

    try:
        root = sa.create_engine(ROOT_URL, isolation_level="AUTOCOMMIT")
        with root.connect() as c:
            c.execute(sa.text(f"DROP DATABASE IF EXISTS {MIG_DB}"))
            c.execute(sa.text(f"CREATE DATABASE {MIG_DB} CHARACTER SET utf8mb4"))
    except Exception as exc:
        pytest.skip(f"MySQL root on {ROOT_URL} not reachable: {exc}")

    url = ROOT_URL.replace("/?", f"/{MIG_DB}?")
    try:
        _alembic(url, "upgrade", "head")
        _alembic(url, "upgrade", "head")  # ikinci çalıştırma no-op
        eng = sa.create_engine(url)
        with eng.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], diff
        _alembic(url, "downgrade", "base")
        _alembic(url, "upgrade", "head")
        eng.dispose()
    finally:
        with root.connect() as c:
            c.execute(sa.text(f"DROP DATABASE IF EXISTS {MIG_DB}"))
        root.dispose()
