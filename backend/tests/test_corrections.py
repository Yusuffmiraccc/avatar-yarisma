from decimal import Decimal as D

from tests.helpers import mk_party, mk_product, receive
from tests.test_butchering import outs, setup_lamb
from tests.test_production import run_reference_order
from tests.test_traceability_recall import build_demo


def _lot(client, h, code):
    return client.get(f"/api/v1/lots/by-code/{code}", headers=h).json()


def test_reverse_production_restores_stock_and_keeps_history(client, auth):
    h = auth("ADMIN")
    oid, sucuk, lots = run_reference_order(client, h)
    client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-2026-045", "quantity": "85", "unit_code": "PACK"}]})
    assert client.post(f"/api/v1/production-orders/{oid}/reverse", headers=auth("OPERATOR"),
                       json={"reason": "yanlış girdi"}).status_code == 403
    r = client.post(f"/api/v1/production-orders/{oid}/reverse", headers=h, json={"reason": "Yanlış çıktı miktarı girildi"})
    assert r.status_code == 200 and r.json()["status"] == "REVERSED"
    assert _lot(client, h, "ET-2026-001")["on_hand_quantity"] == "100.000000"
    suc = _lot(client, h, "SUC-2026-045")
    assert suc["on_hand_quantity"] == "0.000000" and suc["status"] == "CLOSED"
    movs = client.get("/api/v1/inventory/movements", headers=h, params={"lot_id": suc["id"]}).json()["items"]
    assert len(movs) == 2 and any(m["reverses_movement_id"] for m in movs)  # silinmedi, ters kayıt eklendi
    assert client.get("/api/v1/reports/ledger-integrity", headers=h).json()["consistent"] is True
    assert client.post(f"/api/v1/production-orders/{oid}/reverse", headers=h, json={"reason": "tekrar deneme"}).status_code == 409
    ev = client.get("/api/v1/audit-events", headers=h, params={"action": "PRODUCTION_REVERSED"}).json()
    assert ev["total"] == 1 and ev["items"][0]["details"]["reason"] == "Yanlış çıktı miktarı girildi"


def test_reverse_refused_when_output_already_shipped(client, auth):
    h = auth("ADMIN")
    build_demo(client, h)
    oid = client.get("/api/v1/production-orders", headers=h).json()["items"][0]["id"]
    r = client.post(f"/api/v1/production-orders/{oid}/reverse", headers=h, json={"reason": "geri almayı dene"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CANNOT_REVERSE"
    assert _lot(client, h, "ET-2026-001")["on_hand_quantity"] == "0.000000"  # hiçbir şey değişmedi


def test_reverse_butchering(client, auth):
    h = auth("ADMIN")
    oid, lot, p = setup_lamb(client, h, total="287.50")
    client.post(f"/api/v1/butchering-orders/{oid}/waste-records", headers=h, json={"actual_weight": "3", "reason_code": "BONE_WASTE"})
    assert client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json={"outputs": outs(p)}).status_code == 200
    r = client.post(f"/api/v1/butchering-orders/{oid}/reverse", headers=h, json={"reason": "Tartı hatası düzeltmesi"})
    assert r.status_code == 200 and r.json()["status"] == "REVERSED"
    assert _lot(client, h, "KUZU-2026-001")["on_hand_quantity"] == "25.000000"
    assert _lot(client, h, "KUZU-BUT-001")["on_hand_quantity"] == "0.000000"


def test_customer_return_removes_market_from_recall_scope(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h)
    shipment_a = ctx["ships"][0]
    r = client.post(f"/api/v1/shipments/{shipment_a['id']}/return", headers=h, json={"reason": "Müşteri iadesi"})
    assert r.status_code == 200 and r.json()["status"] == "RETURNED"
    assert _lot(client, h, "SUC-2026-045")["on_hand_quantity"] == "30.000000"
    fwd = client.get("/api/v1/traceability/lots/by-code/ET-2026-001/forward", headers=h).json()
    assert {c["customer_name"] for c in fwd["customers"]} == {"Market B", "Market C"}
    assert client.post(f"/api/v1/shipments/{shipment_a['id']}/return", headers=h, json={"reason": "tekrar iade"}).status_code == 409


def test_rework_moves_cost_and_genealogy_and_respects_block(client, auth):
    h = auth("ADMIN")
    et = mk_product(client, h, "ET", "Et")
    kiyma = mk_product(client, h, "KIYMA", "Kıyma", ptype="FINISHED_GOOD")
    src = receive(client, h, "L-SRC", et, 10, "8.00")
    body = {"order_code": "RW-1", "input_lot_id": src["id"], "input_quantity": "10", "output_product_id": kiyma["id"],
            "output_lot_code": "L-KIYMA", "output_quantity": "9", "extra_cost": "10.00", "reason": "Kıymaya çevrildi"}
    r = client.post("/api/v1/rework-orders", headers=h, json=body)
    assert r.status_code == 201, r.text
    out = _lot(client, h, "L-KIYMA")
    assert out["lot_origin_type"] == "REWORK" and out["on_hand_quantity"] == "9.000000"
    assert out["unit_cost"] == "10.0000"  # (10×8 + 10) / 9
    assert _lot(client, h, "L-SRC")["on_hand_quantity"] == "0.000000"
    back = client.get("/api/v1/traceability/lots/by-code/L-KIYMA/backward", headers=h).json()
    assert {n["lot_code"] for n in back["lots"]} == {"L-KIYMA", "L-SRC"} and back["orders"][0]["order_code"] == "RW-1"
    # çıktı girdiyi aşamaz; bloke lot işlenemez
    src2 = receive(client, h, "L-SRC2", et, 5, "8.00")
    bad = client.post("/api/v1/rework-orders", headers=h, json={**body, "order_code": "RW-2", "input_lot_id": src2["id"],
                      "input_quantity": "5", "output_quantity": "6", "output_lot_code": "L-K2"})
    assert bad.status_code == 400
    rid = client.post("/api/v1/recalls", headers=h, json={"recall_code": "R", "reason_code": "Q", "lot_codes": ["L-SRC2"]}).json()["id"]
    client.post(f"/api/v1/recalls/{rid}/activate", headers=h)
    blocked = client.post("/api/v1/rework-orders", headers=h, json={**body, "order_code": "RW-3", "input_lot_id": src2["id"],
                          "input_quantity": "5", "output_quantity": "4", "output_lot_code": "L-K3"})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "LOT_BLOCKED"


def test_quantity_difference_planned_vs_actual(client, auth):
    h = auth("ADMIN")
    oid, sucuk, _ = run_reference_order(client, h)
    # planlanan miktar sonradan DB'de yoksa None kalır; tamamlamadan sonra fark hesaplanır
    from app.db.session import SessionLocal
    from app.models import ProductionOrder
    with SessionLocal() as db:
        o = db.get(ProductionOrder, oid)
        o.planned_quantity, o.planned_unit_code = D("90"), "PACK"
        db.commit()
    r = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "S1", "quantity": "85", "unit_code": "PACK"}]})
    assert r.json()["quantity_difference"] == "-5.000000"
