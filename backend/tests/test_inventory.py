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


def test_lot_cost_and_purchase_prices_require_cost_permission(client, auth):
    admin = auth("ADMIN")
    product = mk_product(client, admin, "COST-ET", "Maliyet Test Eti")
    lot = receive(client, admin, "COST-LOT", product, 10, 5)
    assert "unit_cost" in lot and lot["unit_cost"] == "5.0000"

    for role in ("SALES", "VIEWER"):
        headers = auth(role)
        assert "unit_cost" not in client.get("/api/v1/lots", headers=headers).json()["items"][0]
        assert "unit_cost" not in client.get(f"/api/v1/lots/{lot['id']}", headers=headers).json()
        assert "unit_cost" not in client.get(f"/api/v1/lots/by-code/{lot['lot_code']}", headers=headers).json()

    received = client.post("/api/v1/lots/receipts", headers=auth("OPERATOR"), json={
        "lot_code": "COST-LOT-2", "product_id": product["id"], "quantity": "1", "unit_code": "KG", "unit_cost": "6"})
    assert received.status_code == 201 and received.json()["unit_cost"] == "6.0000"
    transferred = client.post("/api/v1/inventory/transfers", headers=auth("OPERATOR"), json={
        "lot_id": lot["id"], "quantity": "10", "to_location": "WH-2"})
    assert transferred.status_code == 201

    recall = client.post("/api/v1/recalls", headers=admin, json={
        "recall_code": "COST-RECALL", "reason_code": "QUALITY", "lot_codes": [lot["lot_code"]]})
    assert recall.status_code == 201
    recall_id = recall.json()["id"]
    assert client.post(f"/api/v1/recalls/{recall_id}/activate", headers=admin).status_code == 200
    assert client.post(f"/api/v1/recalls/{recall_id}/resolve", headers=admin).status_code == 200
    unblocked = client.post(f"/api/v1/lots/{lot['id']}/unblock", headers=auth("TRACEABILITY_MANAGER"),
                            json={"reason": "Kalite incelemesi tamamlandı"})
    assert unblocked.status_code == 200 and "unit_cost" not in unblocked.json()

    assert client.post(f"/api/v1/products/{product['id']}/prices", headers=admin,
                       json={"price_type": "PURCHASE", "amount": "4", "unit_code": "KG"}).status_code == 201
    assert client.post(f"/api/v1/products/{product['id']}/prices", headers=admin,
                       json={"price_type": "SALE", "amount": "8", "unit_code": "KG"}).status_code == 201
    prices = client.get(f"/api/v1/products/{product['id']}/prices", headers=auth("SALES")).json()
    assert [price["price_type"] for price in prices] == ["SALE"]
    assert {price["price_type"] for price in client.get(
        f"/api/v1/products/{product['id']}/prices", headers=admin).json()} == {"PURCHASE", "SALE"}


def test_sync_catalog_hides_lot_cost_from_sales(client, auth):
    admin = auth("ADMIN")
    product = mk_product(client, admin, "SYNC-COST", "Sync Maliyet")
    receive(client, admin, "SYNC-COST-LOT", product, 10, 5)
    sales_lot = client.get("/api/v1/sync/catalog", headers=auth("SALES")).json()["sellable_lots"][0]
    assert "unit_cost" not in sales_lot
    admin_lot = client.get("/api/v1/sync/catalog", headers=admin).json()["sellable_lots"][0]
    assert admin_lot["unit_cost"] == "5.0000"


def test_receipt_unit_must_match_product_base_unit(client, auth):
    product = mk_product(client, auth("ADMIN"), "UNIT-ET", "Birim Kontrol Eti")
    response = client.post("/api/v1/lots/receipts", headers=auth("ADMIN"), json={
        "lot_code": "UNIT-MISMATCH", "product_id": product["id"], "quantity": "1", "unit_code": "PACK",
        "unit_cost": "1"})
    assert response.status_code == 400
    assert response.json()["error"]["details"]["expected"] == "KG"


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
