"""Test yardımcıları: referans veri ve lot kurulumu API üzerinden."""


def mk_product(client, h, code, name, ptype="RAW_MATERIAL", unit="KG", **kw):
    r = client.post("/api/v1/products", headers=h, json={"code": code, "name": name, "product_type": ptype,
                                                          "base_unit_code": unit, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def mk_party(client, h, kind, code, name, ptype):
    r = client.post(f"/api/v1/{kind}", headers=h, json={"code": code, "name": name, "type": ptype})
    assert r.status_code == 201, r.text
    return r.json()


def receive(client, h, lot_code, product, qty, cost, supplier=None, unit="KG", **kw):
    r = client.post("/api/v1/lots/receipts", headers=h, json={
        "lot_code": lot_code, "product_id": product["id"], "supplier_id": supplier["id"] if supplier else None,
        "quantity": str(qty), "unit_code": unit, "unit_cost": str(cost), **kw})
    assert r.status_code == 201, r.text
    return r.json()
