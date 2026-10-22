from tests.helpers import mk_party, mk_product, receive


def test_receipt_creates_lot_balance_movement(client, auth):
    h = auth("ADMIN")
    et = mk_product(client, h, "ET", "Dana Eti")
    sup = mk_party(client, h, "suppliers", "SUP-1", "Çiftlik A", "RAW_MATERIAL")
    lot = receive(client, h, "ET-2026-001", et, "100", "9.70", sup)
    assert lot["on_hand_quantity"] == "100.000000" and lot["unit_cost"] == "9.7000" and not lot["is_blocked"]
    mv = client.get("/api/v1/inventory/movements", headers=h, params={"lot_id": lot["id"]}).json()
    assert mv["total"] == 1 and mv["items"][0]["movement_type"] == "RECEIPT" and mv["items"][0]["direction"] == "IN"


def test_duplicate_lot_code_409_and_float_rejected(client, auth):
    h = auth("ADMIN")
    et = mk_product(client, h, "ET", "Dana Eti")
    receive(client, h, "L1", et, "1", "1")
    r = client.post("/api/v1/lots/receipts", headers=h, json={"lot_code": "L1", "product_id": et["id"],
                    "quantity": "1", "unit_code": "KG", "unit_cost": "1"})
    assert r.status_code == 409
    r = client.post("/api/v1/lots/receipts", headers=h, json={"lot_code": "L2", "product_id": et["id"],
                    "quantity": 1.5, "unit_code": "KG", "unit_cost": "1"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_expiry_required_when_product_demands_it(client, auth):
    h = auth("ADMIN")
    p = mk_product(client, h, "SUT", "Süt", requires_expiry_date=True)
    r = client.post("/api/v1/lots/receipts", headers=h, json={"lot_code": "S1", "product_id": p["id"],
                    "quantity": "5", "unit_code": "KG", "unit_cost": "1"})
    assert r.status_code == 400
    ok = receive(client, h, "S1", p, 5, 1, expiry_date="2026-12-31")
    assert ok["expiry_date"] == "2026-12-31"


def test_permissions_deny_by_default(client, auth):
    assert client.post("/api/v1/products", headers=auth("VIEWER"), json={}).status_code == 403
    assert client.get("/api/v1/products").status_code == 401
    assert client.get("/api/v1/products", headers=auth("VIEWER")).status_code == 200


def test_adjustment_and_insufficient_stock(client, auth):
    h = auth("ADMIN")
    p = mk_product(client, h, "ET", "Et")
    lot = receive(client, h, "L1", p, 10, 5)
    r = client.post("/api/v1/inventory/adjustments", headers=h, json={"lot_id": lot["id"], "direction": "OUT",
                    "quantity": "11", "reason": "sayım farkı"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    r = client.post("/api/v1/inventory/adjustments", headers=h, json={"lot_id": lot["id"], "direction": "OUT",
                    "quantity": "4", "reason": "sayım farkı"})
    assert r.status_code == 201
    assert client.get(f"/api/v1/lots/{lot['id']}", headers=h).json()["on_hand_quantity"] == "6.000000"
