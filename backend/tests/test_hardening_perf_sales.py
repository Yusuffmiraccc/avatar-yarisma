from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db.session import engine
from app.main import app
from app.models import ButcheringOrder, InventoryBalance, Lot, Product, ProductionOrder
from tests.helpers import mk_party, mk_product, receive


def test_sales_price_override_role_matrix_and_audit(client, auth, db):
    from tests.test_traceability_recall import build_demo

    admin = auth("ADMIN")
    ctx = build_demo(client, admin, ship=(30, 25, 25))
    lot, customer = ctx["suc"], ctx["markets"][0]
    standard = {"customer_id": customer["id"], "lines": [{"lot_id": lot["id"], "quantity": "1"}]}
    for role in ("VIEWER", "OPERATOR"):
        assert client.post("/api/v1/sales", headers=auth(role), json=standard).status_code == 403
    denied = {**standard, "lines": [{**standard["lines"][0], "unit_price": "20"}]}
    assert client.post("/api/v1/sales", headers={**auth("SALES"), "Idempotency-Key": "denied"}, json=denied).status_code == 400
    normal = client.post("/api/v1/sales", headers={**auth("SALES"), "Idempotency-Key": "standard"}, json=standard)
    assert normal.status_code == 201 and normal.json()["lines"][0]["unit_price"] == "24.0000"
    override = {**denied, "lines": [{**denied["lines"][0], "override_reason": "Müşteri sözleşmesi"}]}
    result = client.post("/api/v1/sales", headers={**admin, "Idempotency-Key": "override"}, json=override)
    assert result.status_code == 201 and result.json()["lines"][0]["unit_price"] == "20.0000"
    audit = db.execute(__import__("sqlalchemy").text(
        "SELECT details FROM audit_events WHERE entity_type='sale' ORDER BY id DESC LIMIT 1")).scalar_one()
    import json
    audit_data = json.loads(audit) if isinstance(audit, str) else audit
    audit_str = json.dumps(audit_data, ensure_ascii=False)
    assert "Müşteri sözleşmesi" in audit_str and "24.0000" in str(audit) and "20.0000" in str(audit)


def test_concurrent_sales_cannot_oversell_and_audit_failure_rolls_back(client, auth, monkeypatch):
    admin = auth("ADMIN")
    product = mk_product(client, admin, "RACE", "Race product")
    customer = mk_party(client, admin, "customers", "RACE-C", "Race customer", "MARKET")
    price = client.post(f"/api/v1/products/{product['id']}/prices", headers=admin,
                        json={"price_type": "SALE", "amount": "10", "unit_code": "KG"})
    assert price.status_code == 201
    lot = receive(client, admin, "RACE-L", product, 5, 1)
    sales = auth("SALES")
    barrier = __import__("threading").Barrier(2)

    def sell(index):
        with TestClient(app, raise_server_exceptions=False) as isolated:
            barrier.wait()
            return isolated.post("/api/v1/sales", headers={**sales, "Idempotency-Key": f"race-{index}"},
                                 json={"customer_id": customer["id"], "lines": [{"lot_id": lot["id"], "quantity": "3"}]})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(sell, range(2)))
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert client.get(f"/api/v1/lots/{lot['id']}", headers=admin).json()["on_hand_quantity"] == "2.000000"

    # A later critical sale whose audit write fails must roll back the sale and its stock movement.
    from app.services import sales as sales_svc
    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("simulated audit outage")
    monkeypatch.setattr(sales_svc.audit, "record", fail_audit)
    response = client.post("/api/v1/sales", headers={**sales, "Idempotency-Key": "audit-fails"},
                           json={"customer_id": customer["id"], "lines": [{"lot_id": lot["id"], "quantity": "1"}]})
    assert response.status_code == 500
    assert client.get(f"/api/v1/lots/{lot['id']}", headers=admin).json()["on_hand_quantity"] == "2.000000"


def test_list_serializers_have_bounded_query_count_for_100_rows(client, auth, db):
    product = db.query(Product).first()
    if product is None:
        product = Product(code="PERF-PRODUCT", name="Perf product", product_type="RAW_MATERIAL", base_unit_code="KG")
        db.add(product)
        db.flush()
    db.add_all([ProductionOrder(order_code=f"PERF-P-{i}", production_type="OUTSOURCED", status="DRAFT")
                for i in range(100)])
    db.add_all([ButcheringOrder(order_code=f"PERF-B-{i}", status="DRAFT", animal_type="TEST", input_weight=1,
                                input_unit_code=product.base_unit_code, total_purchase_cost=0,
                                allocation_method="BY_WEIGHT") for i in range(100)])
    db.flush()
    for i in range(100):
        lot = Lot(lot_code=f"PERF-L-{i}", product_id=product.id, received_at=__import__("app.models.types", fromlist=["utcnow"]).utcnow(),
                  initial_quantity=Decimal(1), unit_code=product.base_unit_code, lot_origin_type="PURCHASE", status="ACTIVE")
        db.add(lot)
        db.flush()
        db.add(InventoryBalance(lot_id=lot.id, on_hand_quantity=Decimal(1), reserved_quantity=0))
    db.commit()
    headers = auth("ADMIN")
    measured = {}
    for path in ("/api/v1/production-orders", "/api/v1/butchering-orders", "/api/v1/lots"):
        count = [0]
        def counted(*_args, query_count=count):
            query_count[0] += 1
        event.listen(engine, "before_cursor_execute", counted)
        try:
            response = client.get(path, headers=headers, params={"page_size": 100})
        finally:
            event.remove(engine, "before_cursor_execute", counted)
        assert response.status_code == 200, response.text
        assert response.json()["total"] >= 100
        assert count[0] <= 25, f"{path} used {count[0]} SQL statements for 100 rows"
        measured[path] = count[0]
    print(f"100-row SQL counts: {measured}")

