from datetime import timedelta

from app.core.security import hash_token
from app.db.session import SessionLocal
from app.models import RefreshSession, User
from app.services import auth as auth_svc
from tests.conftest import PASSWORD


def test_health_live_and_ready(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_login_me_and_envelope(client, auth):
    r = client.get("/api/v1/auth/me", headers=auth("SALES"))
    assert r.status_code == 200 and r.json()["roles"] == ["SALES"]
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "UNAUTHENTICATED" and body["request_id"]
    assert r.headers["X-Request-ID"] == body["request_id"]


def test_bad_login_and_validation_envelope(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@avatar.test", "password": "yanlis"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "x"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_refresh_rotation_and_reuse_revokes_family(client, tokens):
    t = tokens("ADMIN")
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r1.status_code == 200
    new = r1.json()["refresh_token"]
    assert new != t["refresh_token"]
    # Kısa ağ retry penceresinde aynı token idempotent biçimde aynı successor'ı verir.
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r2.status_code == 200 and r2.json()["refresh_token"] == new
    # Halefi de dönmüş olsa bile eski token'ın kısa retry penceresi geçerli halefi bulur.
    r3 = client.post("/api/v1/auth/refresh", json={"refresh_token": new})
    assert r3.status_code == 200
    latest = r3.json()["refresh_token"]
    r4 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r4.status_code == 200 and r4.json()["refresh_token"] == latest
    # Pencere geçtikten sonra eski token reuse sayılır ve aile iptal edilir.
    # Move the session timestamp beyond the retry window without sleeping.
    with SessionLocal() as db:
        sess = db.query(RefreshSession).filter_by(token_hash=hash_token(t["refresh_token"])).one()
        replaced_at = sess.revoked_at
    original_utcnow = auth_svc.utcnow
    auth_svc.utcnow = lambda: replaced_at + timedelta(seconds=11)
    try:
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    finally:
        auth_svc.utcnow = original_utcnow
    assert r2.status_code == 401
    r5 = client.post("/api/v1/auth/refresh", json={"refresh_token": latest})
    assert r5.status_code == 401


def test_concurrent_refresh_retry_returns_same_successor(client, tokens):
    from concurrent.futures import ThreadPoolExecutor

    token = tokens("ADMIN")["refresh_token"]
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert first.status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post("/api/v1/auth/refresh", json={"refresh_token": token}), range(2)))
    assert all(r.status_code == 200 for r in responses)
    assert {r.json()["refresh_token"] for r in responses} == {first.json()["refresh_token"]}


def test_simultaneous_first_refresh_preserves_single_successor(client, tokens):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi.testclient import TestClient

    from app.main import app

    token = tokens("ADMIN")["refresh_token"]
    barrier = Barrier(2)

    def refresh_once(_):
        with TestClient(app, raise_server_exceptions=False) as isolated:
            barrier.wait()
            return isolated.post("/api/v1/auth/refresh", json={"refresh_token": token})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(refresh_once, range(2)))
    assert all(response.status_code == 200 for response in responses), [response.text for response in responses]
    assert len({response.json()["refresh_token"] for response in responses}) == 1
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 200


def test_logout_revokes_refresh(client, tokens):
    t = tokens("ADMIN")
    assert client.post("/api/v1/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_disabled_user_rejected_immediately(client, auth, db):
    h = auth("VIEWER")
    u = db.query(User).filter_by(email="viewer@avatar.test").one()
    u.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_login_rate_limit(client):
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "admin@avatar.test", "password": "x"})
    r = client.post("/api/v1/auth/login", json={"email": "admin@avatar.test", "password": PASSWORD})
    assert r.status_code == 429


def test_login_failures_for_one_email_do_not_lock_other_accounts(client, auth):
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "admin@avatar.test", "password": "wrong"})
    assert client.post("/api/v1/auth/login", json={"email": "viewer@avatar.test", "password": PASSWORD}).status_code == 200


def test_login_ignores_forwarded_ip_from_untrusted_peer(monkeypatch):
    from starlette.requests import Request

    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.0/8")
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"x-forwarded-for", b"192.0.2.1")],
                       "client": ("198.51.100.7", 1234), "server": ("test", 80), "scheme": "http", "query_string": b""})
    try:
        assert auth_svc._client_ip(request) == "198.51.100.7"
    finally:
        get_settings.cache_clear()


def test_unknown_login_uses_dummy_hash(db, monkeypatch):
    from app.core.errors import AppError

    observed = []
    monkeypatch.setattr(auth_svc, "verify_password", lambda password, password_hash: observed.append(password_hash) or False)
    try:
        auth_svc.login(db, "missing@avatar.test", "wrong", None)
    except AppError as error:
        assert error.status_code == 401
    else:
        raise AssertionError("unknown account must fail authentication")
    assert observed == [auth_svc._DUMMY_PASSWORD_HASH]


def test_login_rate_limit_buckets_expire_in_shared_store():
    key = "pair:127.0.0.1:old@avatar.test"
    auth_svc._record_failures([key])
    redis_key = auth_svc._storage_keys([key])[0]
    ttl = auth_svc._redis().ttl(redis_key)
    assert 0 < ttl <= auth_svc.WINDOW
