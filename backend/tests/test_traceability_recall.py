"""Zorunlu senaryo: ET-2026-001 -> URT-2026-045 -> SUC-2026-045 -> Market A/B/C (30/25/30)."""
import threading
from decimal import Decimal as D

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PASSWORD
from tests.helpers import mk_party, mk_product, receive
from tests.test_production import run_reference_order


def build_demo(client, h, ship=(30, 25, 30)):
    oid, sucuk, lots = run_reference_order(client, h)
    r = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-2026-045", "quantity": "85", "unit_code": "PACK"}]})
    assert r.status_code == 200, r.text
    markets = [mk_party(client, h, "customers", f"MKT-{c}", f"Market {c}", "MARKET") for c in "ABC"]
    suc = client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()
    ships = []
    for m, q in zip(markets, ship, strict=True):
        if q == 0:
            continue
        sh = client.post("/api/v1/shipments", headers=h, json={"shipment_code": f"SHP-{m['code']}", "customer_id": m["id"],
                         "lines": [{"lot_id": suc["id"], "quantity": str(q)}]})
        assert sh.status_code == 201, sh.text
        d = client.post(f"/api/v1/shipments/{sh.json()['id']}/dispatch",
                        headers={**h, "Idempotency-Key": f"disp-{m['code']}"})
        assert d.status_code == 200, d.text
        ships.append(sh.json())
    return {"lots": lots, "suc": suc, "markets": markets, "ships": ships, "sucuk": sucuk}


def test_forward_backward_and_recall_end_to_end(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h)
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["on_hand_quantity"] == "0.000000"

    back = client.get("/api/v1/traceability/lots/by-code/SUC-2026-045/backward", headers=h).json()
    codes = {n["lot_code"] for n in back["lots"]}
    assert {"SUC-2026-045", "ET-2026-001", "BAH-2026-001", "BAG-2026-001"} <= codes
    assert back["orders"][0]["order_code"] == "URT-2026-045"
    assert back["suppliers"][0]["code"] == "URETICI-1"

    fwd = client.get("/api/v1/traceability/lots/by-code/ET-2026-001/forward", headers=h).json()
    assert {n["lot_code"] for n in fwd["lots"]} == {"ET-2026-001", "SUC-2026-045"}
    cust = {c["customer_name"]: D(c["total_quantity"]) for c in fwd["customers"]}
    assert cust == {"Market A": D(30), "Market B": D(25), "Market C": D(30)}
    assert fwd["second_tier"] == []
    suc_node = next(n for n in fwd["lots"] if n["lot_code"] == "SUC-2026-045")
    assert D(suc_node["origin_share"]) > D("0.9")

    rc = client.post("/api/v1/recalls", headers=h, json={"recall_code": "RCL-2026-001", "reason_code": "QUALITY",
                     "reason_text": "ET-2026-001 kalite sorunu", "lot_codes": ["ET-2026-001"]})
    assert rc.status_code == 201, rc.text
    rid = rc.json()["id"]
    sim = client.get(f"/api/v1/recalls/{rid}/simulation", headers=h).json()
    assert sum(D(c["total_quantity"]) for c in sim["customers"]) == D(85)
    assert client.get("/api/v1/lots/by-code/ET-2026-001", headers=h).json()["is_blocked"] is False

    act = client.post(f"/api/v1/recalls/{rid}/activate", headers=h)
    assert act.status_code == 200, act.text
    body = act.json()
    assert body["status"] == "ACTIVE" and len(body["impacts"]) == 3 and D(body["total_shipped_quantity"]) == D(85)
    assert {l["lot_code"]: l["role"] for l in body["lots"]} == {"ET-2026-001": "ORIGIN", "SUC-2026-045": "DERIVED"}
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["is_blocked"] is True
    assert client.post(f"/api/v1/recalls/{rid}/activate", headers=h).status_code == 409

    imp = body["impacts"][0]
    p = client.patch(f"/api/v1/recalls/{rid}/impacts/{imp['id']}", headers=h, json={"contact_status": "CONTACTED"})
    assert p.status_code == 200 and p.json()["contact_status"] == "CONTACTED"

    tm = auth("TRACEABILITY_MANAGER")
    assert client.post(f"/api/v1/lots/{ctx['suc']['id']}/unblock", headers=tm,
                       json={"reason": "erken açma denemesi"}).status_code == 409
    assert client.post(f"/api/v1/recalls/{rid}/resolve", headers=auth("OPERATOR")).status_code == 403
    assert client.post(f"/api/v1/recalls/{rid}/resolve", headers=tm).json()["status"] == "RESOLVED"
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["is_blocked"] is True
    assert client.post(f"/api/v1/lots/{ctx['suc']['id']}/unblock", headers=auth("SALES"),
                       json={"reason": "yetkisiz deneme"}).status_code == 403
    ok = client.post(f"/api/v1/lots/{ctx['suc']['id']}/unblock", headers=tm, json={"reason": "Laboratuvar sonucu temiz"})
    assert ok.status_code == 200 and ok.json()["is_blocked"] is False


def test_unknown_unlinked_lot_and_duplicate_recall_origins(client, auth):
    h = auth("ADMIN")
    product = mk_product(client, h, "RAW-ORPHAN", "İlişkisiz hammadde")
    lot = receive(client, h, "LOT-ORPHAN-001", product, 5, "1.00")

    unknown = client.get("/api/v1/traceability/lots/by-code/LOT-UNKNOWN/forward", headers=h)
    assert unknown.status_code == 404

    forward = client.get(f"/api/v1/traceability/lots/{lot['id']}/forward", headers=h)
    assert forward.status_code == 200, forward.text
    result = forward.json()
    assert [node["lot_id"] for node in result["lots"]] == [lot["id"]]
    assert result["shipments"] == [] and result["customers"] == []

    recall = client.post("/api/v1/recalls", headers=h, json={
        "recall_code": "RCL-ORPHAN-001", "reason_code": "QUALITY",
        "lot_codes": ["LOT-ORPHAN-001", "LOT-ORPHAN-001"],
    })
    assert recall.status_code == 201, recall.text
    origins = [row for row in recall.json()["lots"] if row["role"] == "ORIGIN"]
    assert len(origins) == 1 and origins[0]["lot_id"] == lot["id"]


def test_recalled_lot_cannot_be_sold_or_shipped(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h, ship=(30, 25, 25))
    rid = client.post("/api/v1/recalls", headers=h, json={"recall_code": "R1", "reason_code": "QUALITY",
                      "lot_codes": ["ET-2026-001"]}).json()["id"]
    client.post(f"/api/v1/recalls/{rid}/activate", headers=h)
    suc = ctx["suc"]
    sale = {"customer_id": ctx["markets"][0]["id"], "lines": [{"lot_id": suc["id"], "quantity": "1"}]}
    r = client.post("/api/v1/sales", headers={**auth("SALES"), "Idempotency-Key": "k1"}, json=sale)
    assert r.status_code == 409 and r.json()["error"]["code"] == "LOT_BLOCKED"
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["on_hand_quantity"] == "5.000000"
    sh = client.post("/api/v1/shipments", headers=h, json={"shipment_code": "SHP-X", "customer_id": ctx["markets"][0]["id"],
                     "lines": [{"lot_id": suc["id"], "quantity": "1"}]})
    d = client.post(f"/api/v1/shipments/{sh.json()['id']}/dispatch", headers={**h, "Idempotency-Key": "d-x"})
    assert d.status_code == 409 and d.json()["error"]["code"] == "LOT_BLOCKED"


def test_sale_idempotency_and_stock_movement_per_line(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h, ship=(30, 25, 25))
    suc, s = ctx["suc"], auth("SALES")
    body = {"customer_id": ctx["markets"][0]["id"], "lines": [{"lot_id": suc["id"], "quantity": "2"}]}
    assert client.post("/api/v1/sales", headers=s, json=body).status_code == 400
    r1 = client.post("/api/v1/sales", headers={**s, "Idempotency-Key": "abc"}, json=body)
    assert r1.status_code == 201, r1.text
    r2 = client.post("/api/v1/sales", headers={**s, "Idempotency-Key": "abc"}, json=body)
    assert r2.status_code == 201 and r2.json() == r1.json() and r2.headers["Idempotent-Replay"] == "true"
    body2 = {**body, "lines": [{"lot_id": suc["id"], "quantity": "3"}]}
    r3 = client.post("/api/v1/sales", headers={**s, "Idempotency-Key": "abc"}, json=body2)
    assert r3.status_code == 409 and r3.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["on_hand_quantity"] == "3.000000"
    line = r1.json()["lines"][0]
    assert line["stock_movement_id"] and line["unit_price"] == "24.0000" and r1.json()["total_amount"] == "48.0000"
    big = {**body, "lines": [{"lot_id": suc["id"], "quantity": "4"}]}
    r4 = client.post("/api/v1/sales", headers={**s, "Idempotency-Key": "big"}, json=big)
    assert r4.status_code == 409 and r4.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    v = client.post(f"/api/v1/sales/{r1.json()['id']}/void", headers=h, json={"reason": "yanlış müşteri"})
    assert v.status_code == 200 and v.json()["status"] == "VOIDED"
    assert client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["on_hand_quantity"] == "5.000000"
    movs = client.get("/api/v1/inventory/movements", headers=h, params={"lot_id": suc["id"]}).json()["items"]
    assert any(m["movement_type"] == "RETURN" and m["reverses_movement_id"] for m in movs)


def test_duplicate_dispatch_creates_single_out(client, auth):
    h = auth("ADMIN")
    ctx = build_demo(client, h, ship=(30, 25, 25))
    m, suc = ctx["markets"][0], ctx["suc"]
    sh = client.post("/api/v1/shipments", headers=h, json={"shipment_code": "SHP-D", "customer_id": m["id"],
                     "lines": [{"lot_id": suc["id"], "quantity": "2"}]}).json()
    url = f"/api/v1/shipments/{sh['id']}/dispatch"
    assert client.post(url, headers=h).status_code == 400
    a = client.post(url, headers={**h, "Idempotency-Key": "k"})
    b = client.post(url, headers={**h, "Idempotency-Key": "k"})
    c = client.post(url, headers={**h, "Idempotency-Key": "other"})
    assert a.status_code == 200 and b.json() == a.json()
    assert c.status_code == 409
    outs = [x for x in client.get("/api/v1/inventory/movements", headers=h, params={
        "lot_id": suc["id"], "movement_type": "SHIPMENT"}).json()["items"] if x["source_id"] == sh["id"]]
    assert len(outs) == 1


def _client_as(role):
    c = TestClient(app, raise_server_exceptions=False)
    tok = c.post("/api/v1/auth/login", json={"email": f"{role.lower()}@avatar.test", "password": PASSWORD}).json()["access_token"]
    return c, {"Authorization": f"Bearer {tok}"}


def test_recall_vs_dispatch_race_is_consistent(client, auth, db):
    """Recall aktivasyonu ile dispatch yarışı: SHIPPED olan her sevkiyat recall etki kayıtlarında olmalı;
    kaybeden taraf LOT_BLOCKED almalı; stok tutarlı kalmalı."""
    import pytest
    if db.bind and db.bind.dialect.name == "sqlite":
        pytest.skip("Row-level locking race test requires MySQL (SELECT FOR UPDATE is unsupported in SQLite)")
    h = auth("ADMIN")
    ctx = build_demo(client, h, ship=(30, 25, 20))  # 10 paket kalır
    suc, m = ctx["suc"], ctx["markets"][0]
    rid = client.post("/api/v1/recalls", headers=h, json={"recall_code": "RACE", "reason_code": "QUALITY",
                      "lot_codes": ["ET-2026-001"]}).json()["id"]
    ships = [client.post("/api/v1/shipments", headers=h, json={"shipment_code": f"SHP-RACE-{n}", "customer_id": m["id"],
             "lines": [{"lot_id": suc["id"], "quantity": "1"}]}).json()["id"] for n in range(5)]
    results, barrier = {}, threading.Barrier(len(ships) + 1)

    def disp(sid):
        c, hh = _client_as("ADMIN")
        barrier.wait()
        results[sid] = c.post(f"/api/v1/shipments/{sid}/dispatch", headers={**hh, "Idempotency-Key": f"r{sid}"})

    def act():
        c, hh = _client_as("ADMIN")
        barrier.wait()
        results["act"] = c.post(f"/api/v1/recalls/{rid}/activate", headers=hh)

    ts = [threading.Thread(target=disp, args=(s,)) for s in ships] + [threading.Thread(target=act)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert results["act"].status_code == 200, results["act"].text
    impacts = client.get(f"/api/v1/recalls/{rid}", headers=h).json()["impacts"]
    impacted_ship_ids = {i["shipment_id"] for i in impacts}
    shipped = {s for s in ships if results[s].status_code == 200}
    blocked = {s for s in ships if results[s].status_code == 409}
    assert shipped | blocked == set(ships), {s: results[s].text for s in ships}
    assert all(results[s].json()["error"]["code"] == "LOT_BLOCKED" for s in blocked)
    assert shipped <= impacted_ship_ids
    remaining = D(client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()["on_hand_quantity"])
    assert remaining == D(10) - len(shipped)
