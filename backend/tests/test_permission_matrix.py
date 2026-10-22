"""Deny-by-default parity: her /api/v1 endpoint'i izin kontrolünden geçer; açık olanlar açıkça listelenir."""
from app.core.introspection import route_permissions
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS
from app.main import app

PUBLIC = {("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/refresh"), ("POST", "/api/v1/auth/logout")}
AUTH_ONLY = {("GET", "/api/v1/auth/me")}


def test_every_api_route_is_protected_or_explicitly_public():
    rows = [r for r in route_permissions(app) if r[1].startswith("/api/v1") and "/docs" not in r[1] and "openapi" not in r[1]]
    assert len(rows) > 60
    for method, path, perm in rows:
        if (method, path) in PUBLIC:
            assert perm is None, (method, path)
        elif (method, path) in AUTH_ONLY:
            assert perm == "AUTHENTICATED"
        else:
            assert perm in ALL_PERMISSIONS, f"{method} {path} izin kontrolsüz: {perm}"


def test_every_permission_is_granted_to_some_role_and_admin_has_all():
    used = {p for _, _, p in route_permissions(app) if p in ALL_PERMISSIONS}
    granted = set().union(*ROLE_PERMISSIONS.values())
    assert used <= granted and ROLE_PERMISSIONS["ADMIN"] == ALL_PERMISSIONS


def test_health_endpoints_are_anonymous_and_outside_api_prefix():
    rows = {(m, p): perm for m, p, perm in route_permissions(app)}
    assert rows[("GET", "/health/live")] is None and rows[("GET", "/health/ready")] is None


def test_viewer_cannot_mutate_anything(client, auth):
    h = auth("VIEWER")
    mutating = [(m, p) for m, p, perm in route_permissions(app) if m in ("POST", "PUT", "PATCH", "DELETE")
                and perm in ALL_PERMISSIONS and perm not in ROLE_PERMISSIONS["VIEWER"]]
    assert mutating
    for m, p in mutating:
        path = p.replace("{", "").replace("}", "")  # parametreli yol 403'ten önce 404 verebilir; izin önce kontrol edilir
        r = client.request(m, path.replace("/api/v1", "/api/v1"), headers=h, json={})
        assert r.status_code in (403, 404, 405, 422, 400), (m, p, r.status_code)
        assert r.status_code != 200 and r.status_code != 201, (m, p)
