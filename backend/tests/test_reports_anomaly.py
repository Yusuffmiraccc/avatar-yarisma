from sqlalchemy import text

from app.db.session import engine
from tests.helpers import mk_product, receive
from tests.test_traceability_recall import build_demo


def test_reports_dashboard_costs_stock_and_notification_list(client, auth):
    h = auth("ADMIN")
    build_demo(client, h)
    rid = client.post("/api/v1/recalls", headers=h, json={"recall_code": "R-1", "reason_code": "QUALITY",
                      "lot_codes": ["ET-2026-001"]}).json()["id"]
    client.post(f"/api/v1/recalls/{rid}/activate", headers=h)
    d = client.get("/api/v1/reports/dashboard", headers=h).json()
    assert d["active_recalls"] == 1 and d["blocked_lots"] == 2 and d["completed_production_orders"] == 1
    pc = client.get("/api/v1/reports/production-costs", headers=h).json()["items"][0]
    assert pc["order_code"] == "URT-2026-045" and pc["ekp"] == "18.1588" and pc["ekp_display"] == "18.16"
    assert pc["vkp"] == "24.0000" and pc["margin_percent"] == "24.3383"
    nl = client.get(f"/api/v1/reports/recalls/{rid}/notification-list", headers=h).json()
    assert [(i["customer_name"], i["quantity"]) for i in nl["items"]] == [
        ("Market A", "30.000000"), ("Market B", "25.000000"), ("Market C", "30.000000")]
    assert client.get("/api/v1/reports/ledger-integrity", headers=h).json()["consistent"] is True


def test_ledger_integrity_detects_tampering_and_scan_raises_alert(client, auth):
    h = auth("ADMIN")
    p = mk_product(client, h, "ET", "Et")
    lot = receive(client, h, "L1", p, 10, 5)
    with engine.begin() as c:  # bakiye doğrudan oynandı (uygulama dışı müdahale simülasyonu)
        c.execute(text("UPDATE inventory_balances SET on_hand_quantity = 7 WHERE lot_id = :i"), {"i": lot["id"]})
    rep = client.get("/api/v1/reports/ledger-integrity", headers=h).json()
    assert rep["consistent"] is False and rep["mismatches"][0]["lot_code"] == "L1"
    created = client.post("/api/v1/alerts/scan", headers=h).json()
    assert [a["alert_type"] for a in created] == ["LEDGER_BALANCE_MISMATCH"]
    assert client.post("/api/v1/alerts/scan", headers=h).json() == []  # tekrar üretmez
    assert client.post("/api/v1/alerts/scan", headers=auth("VIEWER")).status_code == 403
