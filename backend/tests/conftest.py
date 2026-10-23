import os

import pytest
import sqlalchemy as sa

ROOT_URL = os.environ.get("TEST_ROOT_URL", "mysql+pymysql://root:change-root-local-only@localhost:3307/?charset=utf8mb4")
TEST_DB = "avatar_test"
os.environ["DATABASE_URL"] = ROOT_URL.replace("/?", f"/{TEST_DB}?")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789"
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://:avatar-test-only@localhost:16379/0")

# Configure settings before importing modules that cache them.
from functools import lru_cache

from fastapi.testclient import TestClient

import app.models
import app.services.bootstrap as _bootstrap
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services import auth as auth_svc

_bootstrap.hash_password = lru_cache(_bootstrap.hash_password)  # testlerde argon2'yi tekrar hesaplama
from app.services.bootstrap import create_user, seed_reference

PASSWORD = "Test-Pass-123!"


@pytest.fixture(scope="session", autouse=True)
def _database():
    root = sa.create_engine(ROOT_URL, isolation_level="AUTOCOMMIT")
    with root.connect() as c:
        c.execute(sa.text(f"CREATE DATABASE IF NOT EXISTS {TEST_DB} CHARACTER SET utf8mb4"))
    root.dispose()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as c:
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
