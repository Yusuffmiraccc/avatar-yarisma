import os

import pytest
import sqlalchemy as sa

TEST_ROOT_URL_DEFAULT = "mysql+pymysql://root:change-root-local-only@localhost:3307/?charset=utf8mb4"
TEST_DB = "avatar_test"

# If DATABASE_URL is not already set by caller, determine target
if "DATABASE_URL" not in os.environ:
    root_url = os.environ.get("TEST_ROOT_URL")
    if root_url and "sqlite" in root_url:
        os.environ["DATABASE_URL"] = root_url
    elif root_url:
        os.environ["DATABASE_URL"] = root_url.replace("/?", f"/{TEST_DB}?")
    else:
        # Auto-detect if MySQL on port 3307 is reachable
        import socket
        can_connect = False
        try:
            s = socket.create_connection(("localhost", 3307), timeout=0.3)
            s.close()
            can_connect = True
        except Exception:
            can_connect = False
        if can_connect:
            os.environ["DATABASE_URL"] = TEST_ROOT_URL_DEFAULT.replace("/?", f"/{TEST_DB}?")
        else:
            os.environ["DATABASE_URL"] = "sqlite:///./avatar_test.db"

os.environ["JWT_SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789"
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://:avatar-test-only@localhost:16379/0")

# Configure settings before importing modules that cache them.
from functools import lru_cache

from fastapi.testclient import TestClient

import app.models
import app.services.bootstrap as _bootstrap
from app.core import security as _sec
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services import auth as auth_svc

# Cache password hashing and verification in tests to prevent CPU slowdowns
_sec.hash_password = lru_cache(_sec.hash_password)
_sec.verify_password = lru_cache(_sec.verify_password)
_bootstrap.hash_password = _sec.hash_password
auth_svc.verify_password = _sec.verify_password

from app.services.bootstrap import create_user, seed_reference

PASSWORD = "Test-Pass-123!"
IS_SQLITE = "sqlite" in engine.url.drivername


@pytest.fixture(scope="session", autouse=True)
def _database():
    if not IS_SQLITE:
        root_url = os.environ.get("TEST_ROOT_URL", TEST_ROOT_URL_DEFAULT)
        root = sa.create_engine(root_url, isolation_level="AUTOCOMMIT")
        try:
            with root.connect() as c:
                c.execute(
                    sa.text(
                        f"CREATE DATABASE IF NOT EXISTS {TEST_DB} "
                        "CHARACTER SET utf8mb4"
                    )
                )
        finally:
            root.dispose()

        with engine.connect() as conn:
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
            try:
                tables = conn.execute(sa.text("SHOW TABLES")).scalars().all()
                for table in tables:
                    conn.execute(sa.text(f"DROP TABLE IF EXISTS `{table}`"))
            finally:
                conn.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
    else:
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as c:
        if IS_SQLITE:
            c.execute(sa.text("PRAGMA foreign_keys = OFF"))
            for t in reversed(Base.metadata.sorted_tables):
                c.execute(sa.text(f"DELETE FROM `{t.name}`"))
            c.execute(sa.text("PRAGMA foreign_keys = ON"))
        else:
            c.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
            for t in reversed(Base.metadata.sorted_tables):
                c.execute(sa.text(f"TRUNCATE TABLE `{t.name}`"))
            c.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
    auth_svc.reset_rate_limits()
    with SessionLocal() as db:
        seed_reference(db)
        for role in ("ADMIN", "OPERATOR", "SALES", "TRACEABILITY_MANAGER", "VIEWER"):
            create_user(db, f"{role.lower()}@avatar.test", PASSWORD, role.title(), [role])
        db.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def _login(client, role: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": f"{role.lower()}@avatar.test", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def tokens(client):
    return lambda role: _login(client, role)


@pytest.fixture
def auth(client):
    """auth('ADMIN') -> Authorization başlığı."""
    return lambda role="ADMIN": {"Authorization": f"Bearer {_login(client, role)['access_token']}"}
