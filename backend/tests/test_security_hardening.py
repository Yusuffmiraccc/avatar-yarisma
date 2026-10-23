from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import _is_unique_violation, get_db
from app.models import User
from app.schemas.common import ApiModel
from scripts import seed_demo


def test_nonlocal_environment_requires_strong_nondefault_jwt_and_database_secret():
    redis_url = SecretStr("redis://:strong-redis-password@localhost:6379/0")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings(environment="production", jwt_secret_key=SecretStr("short"),
                 database_url="mysql+pymysql://avatar:strong-db-password@localhost/db")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        Settings(environment="staging", jwt_secret_key=SecretStr("x" * 32),
                 database_url="mysql+pymysql://avatar:change-me-local-only@localhost/db")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        Settings(environment="production", jwt_secret_key=SecretStr("x" * 32),
                 database_url="mysql+pymysql://avatar@localhost/db")
    assert Settings(environment="production", jwt_secret_key=SecretStr("x" * 32),
                     database_url="mysql+pymysql://avatar:strong-db-password@localhost/db", redis_url=redis_url)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        Settings(environment="production", jwt_secret_key=SecretStr("x" * 32),
                  database_url="mysql+pymysql://avatar:strong-db-password@localhost/db", redis_url=SecretStr("redis://:change-me-local-only@localhost:6379/0"))
    assert Settings(environment="local")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings(environment="production", jwt_secret_key=SecretStr("local-dev-secret-change-me-0123456789abcdef"),
                 database_url="mysql+pymysql://avatar:strong-db-password@localhost/db")


def test_demo_seed_refuses_nonlocal_environment_before_database_access(monkeypatch):
    monkeypatch.setattr(seed_demo, "get_settings", lambda: SimpleNamespace(environment="staging"))
    with pytest.raises(RuntimeError, match="ENVIRONMENT=local"):
        seed_demo.main()


def test_integrity_errors_only_map_unique_conflicts_and_rollback(client, db):
    assert _is_unique_violation(IntegrityError("insert", {}, Exception("UNIQUE constraint failed: users.email")))
    assert not _is_unique_violation(IntegrityError("insert", {}, Exception("FOREIGN KEY constraint failed")))

    generator = get_db()
    session = next(generator)
    session.add(User(email="admin@avatar.test", password_hash="unused", display_name="duplicate"))
    with pytest.raises(AppError) as error:
        next(generator)
    assert error.value.status_code == 409
    assert db.query(User).filter_by(email="admin@avatar.test").count() == 1


def test_api_datetime_serializer_converts_offsets_to_utc():
    class TimestampOut(ApiModel):
        created_at: datetime

    value = datetime(2026, 10, 22, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    assert TimestampOut(created_at=value).model_dump(mode="json")["created_at"] == "2026-10-22T12:00:00.000000Z"


def test_compose_binds_published_services_only_to_loopback():
    from pathlib import Path

    compose = Path(__file__).parents[1].joinpath("docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:3307:3306"' in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert '"$$MYSQL_PASSWORD" = "change-me-local-only"' in compose
    assert '"$$MYSQL_ROOT_PASSWORD" = "change-root-local-only"' in compose
    assert "REDIS_URL: redis://:" in compose
    assert 'image: redis:7.4-alpine' in compose
    assert '"127.0.0.1:6379:6379"' not in compose


def test_shared_rate_limit_is_enforced_across_processes():
    import subprocess
    import sys
    from pathlib import Path

    from app.services import auth as auth_svc

    backend = Path(__file__).parents[1]
    security = (backend / "SECURITY.md").read_text(encoding="utf-8")
    assert "stored in Redis" in security and "atomic Lua scripts" in security

    key = "pair:127.0.0.1:process-boundary@example.test"
    auth_svc.reset_rate_limits()
    auth_svc._record_failures([key] * auth_svc.MAX_ATTEMPTS)
    with pytest.raises(AppError) as local_limit:
        auth_svc._reserve_attempt([key])
    assert local_limit.value.status_code == 429

    child = subprocess.run(
        [sys.executable, "-c", "from app.core.errors import AppError; from app.services.auth import _reserve_attempt; "
         "exec('try:\\n _reserve_attempt([r\"" + key + "\"])\\nexcept AppError as e:\\n print(e.status_code)')"],
        cwd=backend,
        capture_output=True,
        text=True,
        check=False,
    )
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "429"


def test_rate_limit_store_failure_fails_closed(monkeypatch):
    from redis.exceptions import ConnectionError

    from app.services import auth as auth_svc

    class UnavailableRedis:
        def eval(self, *args):
            raise ConnectionError("unavailable")

    monkeypatch.setattr(auth_svc, "_redis", lambda: UnavailableRedis())
    with pytest.raises(AppError) as error:
        auth_svc._reserve_attempt(["pair:127.0.0.1:unavailable@example.test"])
    assert error.value.status_code == 503


def test_readiness_fails_when_rate_limit_store_is_unavailable(client, monkeypatch):
    from app.services import auth as auth_svc

    monkeypatch.setattr(auth_svc, "rate_limit_store_ready", lambda: False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}

def test_seed_demo_does_not_print_password():
    import ast
    from pathlib import Path

    source = Path(seed_demo.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            printed_names = {child.id for arg in node.args for child in ast.walk(arg)
                             if isinstance(child, ast.Name)}
            assert not printed_names.intersection({"DEMO_PASSWORD", "password"})
