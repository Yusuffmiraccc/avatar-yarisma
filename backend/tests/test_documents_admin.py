from datetime import UTC, timedelta

from app.models import Product
from tests.helpers import mk_party, mk_product
from tests.test_traceability_recall import build_demo

INVOICE = """FATURA NO: FTR-2026-0042
Tarih: 15.10.2026
Satıcı: Anadolu Et Ltd
Dana Eti 100 kg 9,70 970,00 Lot: ET-2026-001 SKT: 30.11.2026
Baharat 2 kg 24,00 48,00 Lot: BAH-2026-001
Bağırsak 5 kg 11,60 58,00 Lot: BAG-2026-001
Genel Toplam: 1.076,00
"""


def _catalog(client, h):
    mk_product(client, h, "ET", "Dana Eti")
    mk_product(client, h, "BAHARAT", "Baharat")
    mk_product(client, h, "BAGIRSAK", "Bağırsak")
    return mk_party(client, h, "suppliers", "SUP-1", "Anadolu Et Ltd", "RAW_MATERIAL")


def test_extract_is_only_a_suggestion_until_human_approves(client, auth):
    h = auth("OPERATOR")
    admin = auth("ADMIN")
    sup = _catalog(client, admin)
    r = client.post("/api/v1/documents/extract", headers=h, json={"doc_type": "INVOICE", "text": INVOICE})
    assert r.status_code == 201, r.text
    doc = r.json()
    p = doc["proposed"]
    assert doc["status"] == "PENDING_REVIEW" and p["document_number"] == "FTR-2026-0042" and p["document_date"] == "2026-10-15"
    assert p["supplier"]["matched"]["code"] == "SUP-1" and p["warnings"] == []
    l0 = p["lines"][0]
    assert (l0["quantity"], l0["unit_code"], l0["lot_code"], l0["expiry_date"]) == ("100", "KG", "ET-2026-001", "2026-11-30")
    assert l0["product"]["code"] == "ET" and l0["flags"] == []
    assert client.get("/api/v1/lots", headers=admin).json()["total"] == 0  # onaydan önce kayıt YOK

    costs = {"ET-2026-001": "9.70", "BAH-2026-001": "24.00", "BAG-2026-001": "11.60"}
    lines = [{"product_id": ln["product"]["id"], "lot_code": ln["lot_code"], "quantity": ln["quantity"], "unit_code": ln["unit_code"],
              "unit_cost": costs[ln["lot_code"]], "expiry_date": ln["expiry_date"]} for ln in p["lines"]]
    ok = client.post(f"/api/v1/documents/{doc['id']}/approve", headers=h, json={"supplier_id": sup["id"], "lines": lines})
    assert ok.status_code == 200 and ok.json()["status"] == "APPROVED" and len(ok.json()["resulting_lot_ids"]) == 3
    lot = client.get("/api/v1/lots/by-code/ET-2026-001", headers=h).json()
    assert lot["on_hand_quantity"] == "100.000000" and lot["unit_cost"] == "9.7000" and lot["expiry_date"] == "2026-11-30"
    admin_lot = client.get("/api/v1/lots/by-code/ET-2026-001", headers=auth("ADMIN")).json()
    assert admin_lot["unit_cost"] == "9.7000"
    assert client.post(f"/api/v1/documents/{doc['id']}/approve", headers=h, json={"lines": lines}).status_code == 409


def test_operator_sees_document_purchase_costs(client, auth):
    admin = auth("ADMIN")
    operator = auth("OPERATOR")
    _catalog(client, admin)
    response = client.post("/api/v1/documents/extract", headers=operator,
                           json={"doc_type": "INVOICE", "text": INVOICE})
    assert response.status_code == 201, response.text
    doc = response.json()
    assert any(line.get("unit_cost") is not None for line in doc["proposed"]["lines"])


def test_approval_is_atomic_and_flags_inconsistencies(client, auth):
    admin = auth("ADMIN")
    _catalog(client, admin)
    bad = INVOICE.replace("48,00", "50,00").replace("1.076,00", "1.200,00")
    doc = client.post("/api/v1/documents/extract", headers=admin, json={"text": bad}).json()
    flags = {l["lot_code"]: l["flags"] for l in doc["proposed"]["lines"]}
    assert "TOTAL_MISMATCH" in flags["BAH-2026-001"]
    assert any(w.startswith("GRAND_TOTAL_MISMATCH") for w in doc["proposed"]["warnings"])
    pid = doc["proposed"]["lines"][0]["product"]["id"]
    lines = [{"product_id": pid, "lot_code": "OK-1", "quantity": "1", "unit_code": "KG", "unit_cost": "1"},
             {"product_id": pid, "lot_code": "OK-1", "quantity": "1", "unit_code": "KG", "unit_cost": "1"}]  # ikinci satır çakışır
    r = client.post(f"/api/v1/documents/{doc['id']}/approve", headers=admin, json={"lines": lines})
    assert r.status_code == 409
    assert client.get("/api/v1/lots", headers=admin).json()["total"] == 0  # hiçbiri kaydedilmedi
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=admin).json()["status"] == "PENDING_REVIEW"
    rej = client.post(f"/api/v1/documents/{doc['id']}/reject", headers=admin, json={"note": "Tutarsız belge"})
    assert rej.json()["status"] == "REJECTED"


def test_file_upload_and_unsupported_media(client, auth):
    admin = auth("ADMIN")
    _catalog(client, admin)
    r = client.post("/api/v1/documents/extract-file", headers=admin, files={"file": ("fatura.txt", INVOICE.encode("utf-8"), "text/plain")})
    assert r.status_code == 201 and len(r.json()["proposed"]["lines"]) == 3
    img = client.post("/api/v1/documents/extract-file", headers=admin, files={"file": ("fatura.png", b"\x89PNG", "image/png")})
    assert img.status_code == 415
    assert client.post("/api/v1/documents/extract", headers=auth("VIEWER"), json={"text": INVOICE}).status_code == 403


def test_user_management_and_session_invalidation(client, auth):
    admin = auth("ADMIN")
    assert client.get("/api/v1/users", headers=auth("OPERATOR")).status_code == 403
    r = client.post("/api/v1/users", headers=admin, json={"email": "Yeni@Avatar.test", "password": "uzun-parola-1", "display_name": "Yeni", "roles": ["SALES"]})
    assert r.status_code == 201 and r.json()["email"] == "yeni@avatar.test"
    assert client.post("/api/v1/users", headers=admin, json={"email": "x@a.test", "password": "kisa", "display_name": "x", "roles": ["SALES"]}).status_code == 400
    assert client.post("/api/v1/users", headers=admin, json={"email": "y@a.test", "password": "uzun-parola-1", "display_name": "y", "roles": ["YOK"]}).status_code == 400
    uid = r.json()["id"]
    login = client.post("/api/v1/auth/login", json={"email": "yeni@avatar.test", "password": "uzun-parola-1"}).json()
    h = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    client.patch(f"/api/v1/users/{uid}", headers=admin, json={"roles": ["VIEWER"]})
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401  # rol değişince eski token geçersiz
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 200
    client.post(f"/api/v1/users/{uid}/reset-password", headers=admin, json={"new_password": "baska-parola-22"})
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "yeni@avatar.test", "password": "baska-parola-22"}).status_code == 200
    me = client.get("/api/v1/auth/me", headers=admin).json()
    assert client.patch(f"/api/v1/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 400


def test_audit_events_filter_and_sync_catalog(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h, ship=(30, 25, 25))  # 5 paket kalır
    ev = client.get("/api/v1/audit-events", headers=h, params={"entity_type": "production_order"}).json()
    assert {e["action"] for e in ev["items"]} >= {"PRODUCTION_CREATED", "PRODUCTION_STARTED", "PRODUCTION_COMPLETED"}
    assert client.get("/api/v1/audit-events", headers=auth("OPERATOR")).status_code == 403
    s = client.get("/api/v1/sync/catalog", headers=auth("SALES")).json()
    assert [l["lot_code"] for l in s["sellable_lots"]] == ["SUC-2026-045"] and s["sellable_lots"][0]["sale_price"] == "24.0000"
    assert {c["code"] for c in s["customers"]} == {"MKT-A", "MKT-B", "MKT-C"} and s["server_time"].endswith("Z")
    later = client.get("/api/v1/sync/catalog", headers=h, params={"updated_after": s["server_time"]}).json()
    assert later["products"] == [] and later["customers"] == []  # yalnızca değişenler
    rid = client.post("/api/v1/recalls", headers=h, json={"recall_code": "R", "reason_code": "Q", "lot_codes": ["ET-2026-001"]}).json()["id"]
    client.post(f"/api/v1/recalls/{rid}/activate", headers=h)
    s2 = client.get("/api/v1/sync/catalog", headers=auth("SALES")).json()
    assert s2["sellable_lots"] == [] and ctx["suc"]["id"] in s2["blocked_lot_ids"]


def test_updated_after_normalizes_timezone_and_includes_boundary(client, auth, db):
    h = auth("ADMIN")
    product = mk_product(client, h, "TIME-BOUNDARY", "Sınır Zamanı")
    created_at = db.get(Product, product["id"]).created_at
    boundary = created_at.replace(tzinfo=UTC)
    utc_value = boundary.isoformat().replace("+00:00", "Z")
    offset_value = (boundary + timedelta(hours=3)).isoformat().replace("+00:00", "+03:00")
    for value in (utc_value, boundary.replace(tzinfo=None).isoformat(), offset_value):
        response = client.get("/api/v1/sync/catalog", headers=h, params={"updated_after": value})
        assert response.status_code == 200
        assert product["id"] in {item["id"] for item in response.json()["products"]}


def test_extract_file_rejects_oversize_without_full_read(client, auth):
    response = client.post("/api/v1/documents/extract-file", headers=auth("ADMIN"),
                           files={"file": ("large.txt", b"x" * 5_000_001, "text/plain")})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
