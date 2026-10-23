"""DEMO verisi: PDF'teki zorunlu üç senaryo + ML için sentetik geçmiş. Tekrar çalıştırılabilir (idempotent).

Kullanım:  python -m scripts.seed_demo
Yalnızca yerel/izole veritabanında çalıştırın. Tüm kayıtlar DEMO veridir; gerçek ticari veri değildir.
"""
import os
import sys

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.services.bootstrap import create_user, seed_reference

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Avatar-Demo-2026!")
USERS = [("admin@avatar.demo", "Demo Yönetici", "ADMIN"), ("operator@avatar.demo", "Demo Operatör", "OPERATOR"),
         ("sales@avatar.demo", "Demo Satış", "SALES"), ("trace@avatar.demo", "Demo İzlenebilirlik", "TRACEABILITY_MANAGER"),
         ("viewer@avatar.demo", "Demo Görüntüleyici", "VIEWER")]


def main() -> int:
    if get_settings().environment.strip().lower() != "local":
        raise RuntimeError("Demo seed yalnızca ENVIRONMENT=local ortamında çalıştırılabilir.")
    with SessionLocal() as db:
        seed_reference(db)
        for email, name, role in USERS:
            create_user(db, email, DEMO_PASSWORD, name, [role])
        db.commit()
    c = TestClient(app)
    tok = c.post("/api/v1/auth/login", json={"email": "admin@avatar.demo", "password": DEMO_PASSWORD}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    def post(url, body=None, headers=None, ok=(200, 201), method="POST"):
        r = c.request(method, f"/api/v1{url}", headers={**h, **(headers or {})}, json=body)
        assert r.status_code in ok, f"{url} -> {r.status_code} {r.text}"
        return r.json()

    if c.get("/api/v1/lots/by-code/KUZU-BUT-2026-001", headers=h).status_code == 200:
        print("Demo verisi zaten yüklü; atlanıyor.")
        return 0

    def product(code, name, ptype, unit="KG", **kw):
        return post("/products", {"code": code, "name": name, "product_type": ptype, "base_unit_code": unit, **kw})

    sup = post("/suppliers", {"code": "URETICI-1", "name": "Anadolu Dış Üretim Ltd.", "type": "OUTSOURCED_PROCESSOR",
                              "phone": "+90 212 000 00 01", "email": "uretim@example.test"})
    cust = [post("/customers", {"code": f"MKT-{k}", "name": f"Market {k}", "type": "MARKET",
                                "phone": f"+90 212 000 00 1{i}", "email": f"market{k.lower()}@example.test"})
            for i, k in enumerate("ABC")]
    et, bah, bag = product("ET", "Dana Eti", "RAW_MATERIAL"), product("BAHARAT", "Baharat", "RAW_MATERIAL"), product("BAGIRSAK", "Bağırsak", "RAW_MATERIAL")
    sucuk = product("SUCUK", "Narin Sucuk 1 kg", "FINISHED_GOOD", "PACK")
    post(f"/products/{sucuk['id']}/prices", {"price_type": "SALE", "amount": "24.00", "unit_code": "PACK"})
    kuzu = product("KUZU-CANLI", "Bütün Kuzu", "RAW_MATERIAL")
    cuts = {k: product(f"KUZU-{k}", f"Kuzu {n}", "FINISHED_GOOD") for k, n in (("BUT", "But"), ("SIRT", "Sırt"), ("OMUZ", "Omuz"))}

    # --- AI: sentetik geçmiş + eğitim. Referans emirlerden ÖNCE: bu emirler eğitimde yok, tahminler gerçekleşmeden üretilir ---
    print(post("/ai/synthetic-data", {}))
    models = post("/ai/models/train")
    for k, v in models.items():
        cv = v["metrics"]["cross_validation"]
        print(k, v["model_name"], "n=", v["n_samples"], "iyileşme % (baseline'a göre):", cv["improvement_over_baseline_percent"])

    # --- Görev 1 + 3: dış hizmetle üretim ve lot izlenebilirliği ---
    lots = {}
    for key, prod, code, q, cost in (("et", et, "ET-2026-001", "100", "9.70"), ("bah", bah, "BAH-2026-001", "2", "24.00"),
                                     ("bag", bag, "BAG-2026-001", "5", "11.60")):
        lots[key] = post("/lots/receipts", {"lot_code": code, "product_id": prod["id"], "supplier_id": sup["id"],
                                            "quantity": q, "unit_code": "KG", "unit_cost": cost})
    o = post("/production-orders", {"order_code": "URT-2026-045", "production_type": "OUTSOURCED", "supplier_id": sup["id"]})
    for key, q in (("et", "100"), ("bah", "2"), ("bag", "5")):
        post(f"/production-orders/{o['id']}/inputs", {"lot_id": lots[key]["id"], "quantity": q, "unit_code": "KG"})
    post(f"/production-orders/{o['id']}/service-costs", {"description": "Dış üretim hizmeti", "quantity": "85", "unit_price": "5.50"})
    post(f"/production-orders/{o['id']}/start")
    post("/ai/production-yield/predict", {"production_order_id": o["id"]})  # tamamlanmadan önce tahmin; sapma sonradan görünür
    post(f"/production-orders/{o['id']}/complete", {"outputs": [{"product_id": sucuk["id"], "lot_code": "SUC-2026-045",
                                                                  "quantity": "85", "unit_code": "PACK"}]})
    suc = c.get("/api/v1/lots/by-code/SUC-2026-045", headers=h).json()
    for m, q in zip(cust, (30, 25, 30), strict=True):
        sh = post("/shipments", {"shipment_code": f"SHP-2026-{m['code'][-1]}", "customer_id": m["id"],
                                 "lines": [{"lot_id": suc["id"], "quantity": str(q)}]})
        post(f"/shipments/{sh['id']}/dispatch", headers={"Idempotency-Key": f"seed-dispatch-{m['code']}"})
    post("/recalls", {"recall_code": "RCL-2026-001", "reason_code": "QUALITY",
                      "reason_text": "ET-2026-001 hammadde partisinde kalite sorunu (DEMO)", "lot_codes": ["ET-2026-001"]})

    # --- Görev 2: bütün kuzu parçalama (kaynak tutarsızlığı bilerek korunur) ---
    post("/butchering-recipes/KUZU", {"lines": [
        {"product_id": cuts["BUT"]["id"], "output_type": "CUT", "expected_ratio": "0.4"},
        {"product_id": cuts["SIRT"]["id"], "output_type": "CUT", "expected_ratio": "0.3"},
        {"product_id": cuts["OMUZ"]["id"], "output_type": "CUT", "expected_ratio": "0.2"}]}, ok=(200,), method="PUT")
    lamb = post("/lots/receipts", {"lot_code": "KUZU-2026-001", "product_id": kuzu["id"], "supplier_id": sup["id"],
                                   "quantity": "25", "unit_code": "KG", "unit_cost": "14.04"})
    b = post("/butchering-orders", {"order_code": "PRC-2026-001", "animal_type": "KUZU", "input_weight": "25",
                                    "total_purchase_cost": "351.00", "declared_unit_price": "11.50",
                                    "notes": "PDF örneği: 25 kg × 11,50 = 287,50 ≠ 351,00; parça toplamı 22 kg (DEMO)"})
    post(f"/butchering-orders/{b['id']}/inputs", {"lot_id": lamb["id"], "quantity": "25"})
    post(f"/butchering-orders/{b['id']}/start")
    post("/ai/butchering-output/predict", {"butchering_order_id": b["id"]})
    post(f"/butchering-orders/{b['id']}/complete", {"variance_reason": "Kaynak belgede 3 kg fark açıklanmamış; kayıp olarak işlendi",
         "outputs": [{"product_id": cuts["BUT"]["id"], "lot_code": "KUZU-BUT-2026-001", "actual_weight": "12"},
                     {"product_id": cuts["SIRT"]["id"], "lot_code": "KUZU-SIRT-2026-001", "actual_weight": "6"},
                     {"product_id": cuts["OMUZ"]["id"], "lot_code": "KUZU-OMUZ-2026-001", "actual_weight": "4"}]})

    post("/alerts/scan")
    print("Demo verisi hazır. Giriş: admin@avatar.demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
