from app.models import User
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
    # eski token tekrar → reuse: aile iptal
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r2.status_code == 401
    r3 = client.post("/api/v1/auth/refresh", json={"refresh_token": new})
    assert r3.status_code == 401


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
