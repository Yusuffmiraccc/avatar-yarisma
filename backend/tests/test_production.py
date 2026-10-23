from decimal import Decimal as D

from tests.helpers import mk_party, mk_product, receive


def setup_sucuk(client, h):
    et = mk_product(client, h, "ET", "Dana Eti")
    bah = mk_product(client, h, "BAHARAT", "Baharat")
    bag = mk_product(client, h, "BAGIRSAK", "Bağırsak")
    sucuk = mk_product(client, h, "SUCUK", "Narin Sucuk 1 kg", ptype="FINISHED_GOOD", unit="PACK")
    client.post(f"/api/v1/products/{sucuk['id']}/prices", headers=h,
                json={"price_type": "SALE", "amount": "24.00", "unit_code": "PACK"})
    sup = mk_party(client, h, "suppliers", "URETICI-1", "Dış Üretici", "OUTSOURCED_PROCESSOR")
    lots = {
        "et": receive(client, h, "ET-2026-001", et, 100, "9.70", sup),
        "bah": receive(client, h, "BAH-2026-001", bah, 2, "24.00", sup),
        "bag": receive(client, h, "BAG-2026-001", bag, 5, "11.60", sup),
    }
    return sucuk, sup, lots


def run_reference_order(client, h):
    sucuk, sup, lots = setup_sucuk(client, h)
    o = client.post("/api/v1/production-orders", headers=h, json={"order_code": "URT-2026-045", "supplier_id": sup["id"]}).json()
    oid = o["id"]
    for key, q in (("et", "100"), ("bah", "2"), ("bag", "5")):
        r = client.post(f"/api/v1/production-orders/{oid}/inputs", headers=h,
                        json={"lot_id": lots[key]["id"], "quantity": q, "unit_code": "KG"})
        assert r.status_code == 201, r.text
    r = client.post(f"/api/v1/production-orders/{oid}/service-costs", headers=h,
                    json={"description": "Üretim hizmeti", "quantity": "85", "unit_price": "5.50"})
    assert r.status_code == 201, r.text
    assert client.post(f"/api/v1/production-orders/{oid}/start", headers=h).status_code == 200
    return oid, sucuk, lots


def test_in_progress_does_not_touch_stock(client, auth):
    h = auth("ADMIN")
    _, _, lots = run_reference_order(client, h)
    assert client.get(f"/api/v1/lots/{lots['et']['id']}", headers=h).json()["on_hand_quantity"] == "100.000000"


def test_complete_reference_scenario_cost_and_genealogy(client, auth):
    h = auth("ADMIN")
    oid, sucuk, lots = run_reference_order(client, h)
    r = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-2026-045", "quantity": "85", "unit_code": "PACK"}]})
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["status"] == "COMPLETED"
    assert o["total_input_cost"] == "1076.0000" and o["total_service_cost"] == "467.5000"
    assert o["total_cost"] == "1543.5000"
    assert o["unit_cost_ekp"] == "18.1588" and o["unit_cost_ekp_display"] == "18.16"
    assert o["vkp"] == "24.00" or o["vkp"] == "24.0000"
    assert D(o["gross_profit_per_unit"]) == D("5.8412")
    # stok: hammadde düştü, mamul girdi
    assert client.get(f"/api/v1/lots/{lots['et']['id']}", headers=h).json()["on_hand_quantity"] == "0.000000"
    suc = client.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()
    assert suc["on_hand_quantity"] == "85.000000" and suc["unit_cost"] == "18.1588"
    # ikinci tamamlama reddedilir
    r2 = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-X", "quantity": "85", "unit_code": "PACK"}]})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_complete_rolls_back_everything_on_failure(client, auth):
    h = auth("ADMIN")
    oid, sucuk, lots = run_reference_order(client, h)
    # aynı mamul lot kodu zaten varsa tamamlama başarısız → hammadde stoğu geri gelmeli
    client.post("/api/v1/lots/receipts", headers=h, json={"lot_code": "SUC-2026-045", "product_id": sucuk["id"],
                "quantity": "1", "unit_code": "PACK", "unit_cost": "1"})
    r = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-2026-045", "quantity": "85", "unit_code": "PACK"}]})
    assert r.status_code == 409
    assert client.get(f"/api/v1/lots/{lots['et']['id']}", headers=h).json()["on_hand_quantity"] == "100.000000"
    assert client.get(f"/api/v1/production-orders/{oid}", headers=h).json()["status"] == "IN_PROGRESS"


def test_production_output_unit_must_match_product_base_unit(client, auth):
    h = auth("ADMIN")
    oid, sucuk, lots = run_reference_order(client, h)
    result = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "BAD-UNIT", "quantity": "85", "unit_code": "KG"}]})
    assert result.status_code == 400
    assert client.get(f"/api/v1/lots/{lots['et']['id']}", headers=h).json()["on_hand_quantity"] == "100.000000"
    assert client.get(f"/api/v1/production-orders/{oid}", headers=h).json()["status"] == "IN_PROGRESS"


def test_insufficient_input_stock_blocks_completion(client, auth):
    h = auth("ADMIN")
    sucuk, _, lots = setup_sucuk(client, h)
    oid = client.post("/api/v1/production-orders", headers=h, json={"order_code": "URT-1"}).json()["id"]
    client.post(f"/api/v1/production-orders/{oid}/inputs", headers=h,
                json={"lot_id": lots["et"]["id"], "quantity": "150", "unit_code": "KG"})
    client.post(f"/api/v1/production-orders/{oid}/start", headers=h)
    r = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "S1", "quantity": "10", "unit_code": "PACK"}]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_operator_can_manage_viewer_cannot(client, auth):
    assert client.post("/api/v1/production-orders", headers=auth("VIEWER"), json={"order_code": "X"}).status_code == 403
    assert client.post("/api/v1/production-orders", headers=auth("OPERATOR"), json={"order_code": "X"}).status_code == 201
