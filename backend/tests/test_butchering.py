from decimal import Decimal as D

from tests.helpers import mk_product, receive


def setup_lamb(client, h, total="351.00", price="11.50", weight="25"):
    kuzu = mk_product(client, h, "KUZU", "Bütün Kuzu")
    but = mk_product(client, h, "KUZU-BUT", "Kuzu But", ptype="FINISHED_GOOD")
    sirt = mk_product(client, h, "KUZU-SIRT", "Kuzu Sırt", ptype="FINISHED_GOOD")
    omuz = mk_product(client, h, "KUZU-OMUZ", "Kuzu Omuz", ptype="FINISHED_GOOD")
    lot = receive(client, h, "KUZU-2026-001", kuzu, weight, str(D(total) / D(weight)))
    r = client.post("/api/v1/butchering-orders", headers=h, json={
        "order_code": "PRC-2026-001", "animal_type": "KUZU", "input_weight": weight, "input_unit_code": "KG",
        "total_purchase_cost": total, "declared_unit_price": price})
    assert r.status_code == 201, r.text
    oid = r.json()["id"]
    assert client.post(f"/api/v1/butchering-orders/{oid}/inputs", headers=h,
                       json={"lot_id": lot["id"], "quantity": weight}).status_code == 201
    assert client.post(f"/api/v1/butchering-orders/{oid}/start", headers=h).status_code == 200
    return oid, lot, {"but": but, "sirt": sirt, "omuz": omuz}


def outs(p, but="12", sirt="6", omuz="4"):
    return [
        {"product_id": p["but"]["id"], "lot_code": "KUZU-BUT-001", "actual_weight": but},
        {"product_id": p["sirt"]["id"], "lot_code": "KUZU-SIRT-001", "actual_weight": sirt},
        {"product_id": p["omuz"]["id"], "lot_code": "KUZU-OMUZ-001", "actual_weight": omuz},
    ]


def test_source_inconsistency_is_flagged_not_fixed(client, auth):
    h = auth("ADMIN")
    oid, _, _ = setup_lamb(client, h)
    o = client.get(f"/api/v1/butchering-orders/{oid}", headers=h).json()
    f = [x for x in o["findings"] if x["code"] == "SOURCE_COST_MISMATCH"][0]
    assert f["details"] == {"computed_total": "287.5000", "declared_total": "351.0000", "difference": "63.5000"}
    assert o["total_purchase_cost"] == "351.0000"  # sessizce düzeltilmedi
    alerts = client.get("/api/v1/alerts", headers=h).json()
    assert any(a["alert_type"] == "SOURCE_COST_MISMATCH" for a in alerts["items"])


def test_22kg_vs_25kg_requires_variance_approval(client, auth):
    h = auth("ADMIN")
    oid, _, p = setup_lamb(client, h)
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json={"outputs": outs(p)})
    assert r.status_code == 409 and r.json()["error"]["code"] == "WEIGHT_VARIANCE_EXCEEDED"
    assert r.json()["error"]["details"]["difference"] == "3.000000"
    # operatör onaylayamaz
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=auth("OPERATOR"),
                    json={"outputs": outs(p), "variance_reason": "Kemik ve kan kaybı tartıldı"})
    assert r.status_code == 403
    # yetkili gerekçeli onay → tamamlanır, toplam dağıtım = toplam maliyet
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h,
                    json={"outputs": outs(p), "variance_reason": "Kemik ve kan kaybı tartıldı"})
    assert r.status_code == 200, r.text
    o = r.json()
    assert D(o["allocated_total"]) == D("351.0000")
    assert o["variance"]["allocated_cost"] == "42.1200"  # 3/25 × 351
    assert D(o["sellable_cost_total"]) + D(o["waste_cost_total"]) == D("351.0000")
    # stok: kuzu tükendi, parçalar lotlu stokta
    assert client.get("/api/v1/lots/by-code/KUZU-2026-001", headers=h).json()["on_hand_quantity"] == "0.000000"
    assert client.get("/api/v1/lots/by-code/KUZU-BUT-001", headers=h).json()["on_hand_quantity"] == "12.000000"


def test_output_heavier_than_input_requires_reason_and_approval(client, auth):
    h = auth("ADMIN")
    oid, _, products = setup_lamb(client, h)
    outputs = outs(products, "13", "7", "6")  # çıktı 26 kg, girdi 25 kg
    assert client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json={"outputs": outputs}).status_code == 409
    body = {"outputs": outputs, "variance_reason": "Çıktı tartısı yeniden doğrulandı"}
    assert client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=auth("OPERATOR"), json=body).status_code == 403
    result = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["weight_difference"] == "-1.000000"
    assert result.json()["variance"]["variance_weight"] == "-1.000000"
    assert result.json()["variance"]["allocated_cost"] == "0.0000"


def test_positive_weight_tolerance_accepts_boundary(client, auth, monkeypatch):
    from types import SimpleNamespace

    from app.services import butchering as svc
    monkeypatch.setattr(svc, "get_settings", lambda: SimpleNamespace(weight_tolerance_kg="1.000"))
    h = auth("ADMIN")
    oid, _, products = setup_lamb(client, h)
    result = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h,
                         json={"outputs": outs(products, "10", "8", "6")})
    assert result.status_code == 200, result.text
    assert result.json()["weight_difference"] == "1.000000"
    assert result.json()["variance"]["tolerance_weight"] == "1.000000"


def test_positive_weight_tolerance_rejects_value_outside_boundary(client, auth, monkeypatch):
    from types import SimpleNamespace

    from app.services import butchering as svc
    monkeypatch.setattr(svc, "get_settings", lambda: SimpleNamespace(weight_tolerance_kg="1.000"))
    h = auth("ADMIN")
    oid, lot, products = setup_lamb(client, h)
    result = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h,
                         json={"outputs": outs(products, "10", "8", "5")})
    assert result.status_code == 409 and result.json()["error"]["code"] == "WEIGHT_VARIANCE_EXCEEDED"
    assert client.get(f"/api/v1/lots/{lot['id']}", headers=h).json()["on_hand_quantity"] == "25.000000"


def test_butchering_output_unit_must_match_product_base_unit(client, auth):
    h = auth("ADMIN")
    oid, lot, products = setup_lamb(client, h)
    outputs = outs(products)
    outputs[0]["unit_code"] = "PACK"
    result = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h,
                         json={"outputs": outputs, "variance_reason": "Birim tutarlılığı regresyon denetimi"})
    assert result.status_code == 400
    assert client.get(f"/api/v1/lots/{lot['id']}", headers=h).json()["on_hand_quantity"] == "25.000000"
    assert client.get(f"/api/v1/butchering-orders/{oid}", headers=h).json()["status"] == "IN_PROGRESS"


def test_waste_closes_balance_no_stock_in_and_cost_shared(client, auth):
    h = auth("ADMIN")
    oid, _, p = setup_lamb(client, h)
    r = client.post(f"/api/v1/butchering-orders/{oid}/waste-records", headers=h,
                    json={"actual_weight": "3", "reason_code": "BONE_WASTE"})
    assert r.status_code == 201
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json={"outputs": outs(p)})
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["weight_difference"] == "0.000000" and o["variance"] is None
    assert o["waste_records"][0]["allocated_cost"] == "42.1200"
    assert D(o["allocated_total"]) == D("351.0000")
    movs = client.get("/api/v1/inventory/movements", headers=h, params={"movement_type": "WASTE"}).json()
    assert movs["total"] == 0  # fire stok hareketi üretmez
    # lot maliyeti fire payını içermez: but 12 kg × (351×12/25)/12 = 14.04/kg
    assert client.get("/api/v1/lots/by-code/KUZU-BUT-001", headers=h).json()["unit_cost"] == "14.0400"


def test_by_value_fails_closed_without_waste_valuation(client, auth):
    h = auth("ADMIN")
    kuzu = mk_product(client, h, "KUZU", "Kuzu")
    but = mk_product(client, h, "BUT", "But", ptype="FINISHED_GOOD")
    client.post(f"/api/v1/products/{but['id']}/prices", headers=h, json={"price_type": "SALE", "amount": "20", "unit_code": "KG"})
    lot = receive(client, h, "K1", kuzu, 10, 10)
    oid = client.post("/api/v1/butchering-orders", headers=h, json={"order_code": "P1", "animal_type": "KUZU",
                      "input_weight": "10", "total_purchase_cost": "100", "allocation_method": "BY_VALUE"}).json()["id"]
    client.post(f"/api/v1/butchering-orders/{oid}/inputs", headers=h, json={"lot_id": lot["id"], "quantity": "10"})
    client.post(f"/api/v1/butchering-orders/{oid}/start", headers=h)
    client.post(f"/api/v1/butchering-orders/{oid}/waste-records", headers=h, json={"actual_weight": "2", "reason_code": "OTHER"})
    body = {"outputs": [{"product_id": but["id"], "lot_code": "B1", "actual_weight": "8"}]}
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "BY_VALUE_WASTE_VALUATION_REQUIRED"
    assert client.get("/api/v1/lots/by-code/K1", headers=h).json()["on_hand_quantity"] == "10.000000"
    body["waste_unit_value"] = "5"
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json=body)
    assert r.status_code == 200, r.text
    assert D(r.json()["allocated_total"]) == D("100.0000")
    # 8×20=160 çıktı değeri, 2×5=10 fire değeri → fire payı 100×10/170
    assert r.json()["waste_records"][0]["allocated_cost"] == "5.8824"


def test_recipe_expected_vs_actual(client, auth):
    h = auth("ADMIN")
    oid, _, p = setup_lamb(client, h, total="287.50")
    r = client.put("/api/v1/butchering-recipes/KUZU", headers=h, json={"lines": [
        {"product_id": p["but"]["id"], "output_type": "CUT", "expected_ratio": "0.4"},
        {"product_id": p["sirt"]["id"], "output_type": "CUT", "expected_ratio": "0.3"},
        {"product_id": p["omuz"]["id"], "output_type": "CUT", "expected_ratio": "0.2"}]})
    assert r.status_code == 200 and r.json()["ratio_sum"] == "0.900000"
    client.post(f"/api/v1/butchering-orders/{oid}/waste-records", headers=h,
                json={"actual_weight": "3", "reason_code": "BONE_WASTE"})
    r = client.post(f"/api/v1/butchering-orders/{oid}/complete", headers=h, json={"outputs": outs(p)})
    assert r.status_code == 200, r.text
    but = [o for o in r.json()["outputs"] if o["lot_code"] == "KUZU-BUT-001"][0]
    assert but["expected_weight"] == "10.000000" and but["deviation_weight"] == "2.000000"
