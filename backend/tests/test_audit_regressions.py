import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from time import perf_counter

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.body_limit import UploadBodyLimitMiddleware
from app.core.errors import validated_request_id
from app.db.session import engine
from app.main import app
from app.models import (
    InventoryBalance,
    Lot,
    LotGenealogyEdge,
    Recall,
    RecallCustomerImpact,
    RecallLot,
    Sale,
    SaleLine,
    Shipment,
    ShipmentLine,
    User,
)
from app.models.types import utcnow
from tests.helpers import mk_party, mk_product, receive
from tests.test_butchering import outs, setup_lamb
from tests.test_production import run_reference_order

_COST_KEYS = {
    "unit_cost", "cost_snapshot", "allocated_cost", "total_purchase_cost", "sellable_cost_total",
    "waste_cost_total", "allocated_total", "total_input_cost", "total_service_cost", "total_cost",
    "unit_cost_ekp", "unit_cost_ekp_display", "predicted_cost", "baseline_cost", "actual_cost",
    "stock_value", "value", "total_value", "ekp", "ekp_display", "vkp", "gross_profit_per_unit",
    "margin_percent", "gross_profit_total",
}


def _assert_no_cost_fields(value):
    if isinstance(value, dict):
        assert not (_COST_KEYS & value.keys()), _COST_KEYS & value.keys()
        for nested in value.values():
            _assert_no_cost_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_cost_fields(nested)


def test_cost_fields_require_costs_read_across_reports_and_order_endpoints(client, auth):
    admin = auth("ADMIN")
    order_id, product, _ = run_reference_order(client, admin)
    completed = client.post(f"/api/v1/production-orders/{order_id}/complete", headers=admin, json={"outputs": [
        {"product_id": product["id"], "lot_code": "COST-SECURE-OUT", "quantity": "85", "unit_code": "PACK"}]})
    assert completed.status_code == 200, completed.text

    butcher_id, _, products = setup_lamb(client, admin, total="351.00", weight="25")
    done = client.post(f"/api/v1/butchering-orders/{butcher_id}/complete", headers=admin,
                       json={"outputs": outs(products), "variance_reason": "Audit test variance approved"})
    assert done.status_code == 200, done.text

    admin_prod = client.get(f"/api/v1/production-orders/{order_id}", headers=admin).json()
    admin_butcher = client.get(f"/api/v1/butchering-orders/{butcher_id}", headers=admin).json()
    assert "total_cost" in admin_prod and "unit_cost" in admin_prod["inputs"][0]
    assert "total_purchase_cost" in admin_butcher and "allocated_cost" in admin_butcher["outputs"][0]
    assert "stock_value" in client.get("/api/v1/reports/dashboard", headers=admin).json()

    for role in ("VIEWER", "SALES", "TRACEABILITY_MANAGER"):
        headers = auth(role)
        paths = ["/api/v1/reports/dashboard", "/api/v1/reports/production-costs",
                 "/api/v1/reports/stock-valuation"]
        if role != "SALES":  # SALES deliberately has no production:read or butchering:read permission.
            paths.extend(("/api/v1/production-orders", f"/api/v1/production-orders/{order_id}",
                          "/api/v1/butchering-orders", f"/api/v1/butchering-orders/{butcher_id}"))
        for path in paths:
            response = client.get(path, headers=headers)
            assert response.status_code == 200, (role, path, response.text)
            _assert_no_cost_fields(response.json())


def test_cost_mismatch_alert_and_butchering_finding_do_not_leak_to_operator(client, auth):
    admin = auth("ADMIN")
    order_id, _, _ = setup_lamb(client, admin)  # deliberately inconsistent purchase total/price

    operator = auth("TRACEABILITY_MANAGER")
    order_response = client.get(f"/api/v1/butchering-orders/{order_id}", headers=operator)
    alerts_response = client.get("/api/v1/alerts", headers=operator)
    assert order_response.status_code == 200 and alerts_response.status_code == 200
    body = json.dumps({"order": order_response.json(), "alerts": alerts_response.json()})
    assert "287.5000" not in body
    assert "351.0000" not in body
    assert "63.5000" not in body


def test_parallel_failed_logins_reserve_rate_limit_slots_atomically():
    count = 16
    barrier = Barrier(count)

    def attempt(_):
        with TestClient(app, raise_server_exceptions=False) as isolated:
            barrier.wait()
            return isolated.post("/api/v1/auth/login", json={"email": "admin@avatar.test", "password": "wrong"}).status_code

    with ThreadPoolExecutor(max_workers=count) as pool:
        statuses = list(pool.map(attempt, range(count)))
    assert statuses.count(429) >= count - 10
    assert statuses.count(401) <= 10
    with TestClient(app, raise_server_exceptions=False) as isolated:
        second_user = isolated.post("/api/v1/auth/login", json={
            "email": "viewer@avatar.test", "password": "wrong"})
    assert second_user.status_code == 401


def test_request_id_validation_preserves_good_ids_and_replaces_bad_values(client):
    valid = "req-2026.10:case_7"
    assert validated_request_id(valid) == valid
    for invalid in ("", "x" * 129, "not/a-safe-id", "line\nbreak", "control\x01"):
        result = validated_request_id(invalid)
        assert result != invalid and re.fullmatch(r"[0-9a-f-]{36}", result)
    response = client.get("/health/live", headers={"X-Request-ID": valid})
    assert response.headers["X-Request-ID"] == valid
    response = client.get("/health/live", headers={"X-Request-ID": "z" * 200})
    assert response.headers["X-Request-ID"] != "z" * 200


def test_upload_body_middleware_rejects_streaming_over_limit_without_content_length():
    limit = 1024
    calls = []
    messages = [{"type": "http.request", "body": b"x" * (limit + 1), "more_body": False}]

    async def receive():
        return messages.pop(0)

    async def send(message):
        calls.append(message)

    async def downstream(scope, receive, send):
        await receive()
        raise AssertionError("oversized body reached downstream parser")

    middleware = UploadBodyLimitMiddleware(downstream, path="/api/v1/documents/extract-file",
                                           max_body_bytes=limit)
    scope = {"type": "http", "method": "POST", "path": "/api/v1/documents/extract-file", "headers": []}
    asyncio.run(middleware(scope, receive, send))
    assert calls[0]["status"] == 413
    body = calls[-1]["body"]
    assert b"PAYLOAD_TOO_LARGE" in body


def test_pdf_upload_rejects_extension_content_mismatch_and_malformed_pdf(client, auth):
    headers = auth("ADMIN")
    mismatch = client.post("/api/v1/documents/extract-file", headers=headers,
                           files={"file": ("invoice.pdf", b"plain text", "application/pdf")})
    assert mismatch.status_code == 415
    malformed = client.post("/api/v1/documents/extract-file", headers=headers,
                            files={"file": ("invoice.pdf", b"%PDF-not-a-valid-pdf", "application/pdf")})
    assert malformed.status_code == 422


def test_100_row_lists_and_wide_traceability_graph_have_bounded_queries(client, auth, db):
    admin = auth("ADMIN")
    admin_id = db.query(User).filter_by(email="admin@avatar.test").one().id
    product = mk_product(client, admin, "BATCH-PERF", "Batch performance")
    customer = mk_party(client, admin, "customers", "BATCH-C", "Batch customer", "MARKET")
    origin = receive(client, admin, "BATCH-ROOT", product, 1, 1)
    root_lot = db.query(Lot).filter_by(id=origin["id"]).one()

    shipments = [Shipment(shipment_code=f"BATCH-S-{n}", customer_id=customer["id"], status="DRAFT",
                          created_by=admin_id) for n in range(100)]
    db.add_all(shipments)
    db.flush()
    sales = [Sale(sale_code=f"BATCH-SALE-{n}", customer_id=customer["id"], shipment_id=shipments[n].id,
                  status="COMPLETED", sold_at=utcnow(), total_amount=Decimal(10), created_by=admin_id)
             for n in range(100)]
    db.add_all(sales)
    db.flush()
    db.add_all([ShipmentLine(shipment_id=shipments[n].id, line_number=1, product_id=product["id"],
                             lot_id=root_lot.id, quantity=Decimal(1), unit_code="KG") for n in range(100)])
    db.add_all([SaleLine(sale_id=sales[n].id, line_number=1, product_id=product["id"], lot_id=root_lot.id,
                         quantity=Decimal(1), unit_code="KG", unit_price=Decimal(10), line_total=Decimal(10))
                for n in range(100)])
    recalls = [Recall(recall_code=f"BATCH-R-{n}", status="DRAFT", reason_code="TEST", created_by=admin_id)
               for n in range(100)]
    db.add_all(recalls)
    db.flush()
    db.add_all([RecallLot(recall_id=recall.id, lot_id=root_lot.id, role="ORIGIN") for recall in recalls])
    db.add_all([RecallCustomerImpact(recall_id=recall.id, customer_id=customer["id"], lot_id=root_lot.id,
                                    quantity=Decimal(1), unit_code="KG") for recall in recalls])

    children = [Lot(lot_code=f"BATCH-CHILD-{n}", product_id=product["id"], initial_quantity=Decimal(1),
                    unit_code="KG", lot_origin_type="PRODUCTION", received_at=utcnow()) for n in range(100)]
    db.add_all(children)
    db.flush()
    db.add_all([InventoryBalance(lot_id=child.id, on_hand_quantity=Decimal(1), reserved_quantity=Decimal(0))
                for child in children])
    db.add_all([LotGenealogyEdge(source_lot_id=child.id, target_lot_id=root_lot.id, process_type="REWORK",
                                 process_id=1, source_quantity=Decimal(1), source_unit_code="KG",
                                 target_quantity=Decimal(1), target_unit_code="KG") for child in children])
    db.commit()

    measured = {}
    for path in ("/api/v1/sales", "/api/v1/shipments", "/api/v1/recalls",
                 f"/api/v1/traceability/lots/{root_lot.id}/graph",
                 f"/api/v1/traceability/lots/{root_lot.id}/backward"):
        count, started = [0], perf_counter()

        def counted(*_args, query_count=count):
            query_count[0] += 1

        event.listen(engine, "before_cursor_execute", counted)
        try:
            response = client.get(path, headers=admin, params={"page_size": 100})
        finally:
            event.remove(engine, "before_cursor_execute", counted)
        elapsed = perf_counter() - started
        assert response.status_code == 200, (path, response.text)
        measured[path] = (count[0], round(elapsed, 3))
        assert count[0] <= 25, f"{path}: {count[0]} statements for 100 rows/nodes"
    print(f"100-row/query performance (statements, seconds): {measured}")


def test_audit_events_hide_cost_details_without_costs_read(client, auth):
    admin = auth("ADMIN")
    oid, sucuk, _ = run_reference_order(client, admin)
    done = client.post(f"/api/v1/production-orders/{oid}/complete", headers=admin, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-AUDIT", "quantity": "85", "unit_code": "PACK"}]})
    assert done.status_code == 200, done.text
    params = {"action": "PRODUCTION_COMPLETED"}
    assert "ekp" in json.dumps(client.get("/api/v1/audit-events", headers=admin, params=params).json())
    tm = client.get("/api/v1/audit-events", headers=auth("TRACEABILITY_MANAGER"), params=params)
    assert tm.status_code == 200 and tm.json()["total"] == 1
    _assert_no_cost_fields(tm.json())
