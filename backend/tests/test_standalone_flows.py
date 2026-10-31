"""Kapsamlı Bağımsız Akış Doğrulama Testi.

Bu test modülü, dış ağ ve soket bağımlılığı olmaksızın doğrudan
veritabanı transaction'ları, domain modelleri ve servis katmanı üzerinden
10 temel iş akışını uçtan uca doğrular:
1. Hammadde stoğu ve parti kabulü (lots.receive)
2. Dış hizmet üretim emri (URT-2026-045) ve girdi tüketimi
3. Hassas EKP maliyet hesabı (1.543,50 € / 85 pk = 18,16 €)
4. Üretim kabulü ve atomik stok düşümü
5. Kuzu karkas parçalama ve 287,50 € != 351,00 € şartname tutarsızlığı kontrolü
6. Ağırlık bazlı maliyet dağıtımı ve kuruş kaybı önleme (son satıra artık aktarımı)
7. Satış siparişi, katalog fiyat koruması ve stok düşümü
8. Idempotency (mükerrer istek engelleme ve replay)
9. Çift yönlü lot izlenebilirliği (ET-2026-001 -> URT-2026-045 -> SUC-2026-045 -> Market)
10. Geri çağırma (Recall) ve bloke lot satış engeli
"""
from decimal import Decimal as D
import uuid
import pytest

from app.models.catalog import Product, Supplier, Customer, ProductPrice
from app.models.inventory import Lot, InventoryBalance
from app.models.production import ProductionOrder
from app.models.butchering import ButcheringOrder
from app.core.deps import CurrentUser
from app.core.errors import AppError

from app.services import (
    costing,
    lots as lots_svc,
    production as prod_svc,
    butchering as butch_svc,
    sales as sales_svc,
    recall as recall_svc,
    stock as stock_svc,
    idempotency as idemp_svc,
    traceability as trace_svc,
)
from app.models import MlPrediction, StockMovement
from app.schemas.common import redact_cost_data
from app.schemas.production import CompleteIn, OutputIn, ServiceCostIn, ProductionInputIn
from app.schemas.butchering import ButcheringCompleteIn, ButcheringOutputIn, ButcheringInputIn, WasteIn
from app.schemas.sales import SaleIn, SaleLineIn
from pydantic import BaseModel


def make_user(uid=1, role="ADMIN", perms=None):
    if perms is None:
        perms = {
            "admin", "production:create", "production:complete",
            "butchering:create", "butchering:complete", "butchering:approve_variance",
            "sales:create", "recall:create", "recall:manage"
        }
    return CurrentUser(
        id=uid,
        email=f"{role.lower()}@avatar.test",
        display_name=f"Test {role}",
        roles=[role],
        permissions=frozenset(perms)
    )


def test_ekp_production_and_stock_flow(db):
    user = make_user()

    # 1. Tedarikçi ve Ürün Tanımları
    supplier = Supplier(code="SUP-OUT-01", name="Anadolu Dış Üretim", supplier_type="OUTSOURCED_PROCESSOR")
    db.add(supplier)

    et = Product(code="RAW-ET-01", name="Dana Eti", product_type="RAW_MATERIAL", base_unit_code="KG")
    bah = Product(code="RAW-BAH-01", name="Baharat Karışımı", product_type="RAW_MATERIAL", base_unit_code="KG")
    bag = Product(code="RAW-BAG-01", name="Doğal Bağırsak", product_type="RAW_MATERIAL", base_unit_code="KG")
    sucuk = Product(code="FIN-SUC-01", name="Narin Kangal Sucuk", product_type="FINISHED_GOOD", base_unit_code="PACK")
    db.add_all([et, bah, bag, sucuk])
    db.flush()

    # 2. Hammadde Girişleri (ET-2026-001, BAH-2026-001, BAG-2026-001)
    lot_et, bal_et = lots_svc.receive(db, lot_code="ET-2026-001", product_id=et.id, supplier_id=supplier.id,
                                      quantity=D("100"), unit_code="KG", unit_cost=D("9.70"),
                                      received_at=None, expiry_date=None, user_id=user.id, request_id="REQ-REC-01")
    lot_bah, bal_bah = lots_svc.receive(db, lot_code="BAH-2026-001", product_id=bah.id, supplier_id=supplier.id,
                                        quantity=D("2"), unit_code="KG", unit_cost=D("24.00"),
                                        received_at=None, expiry_date=None, user_id=user.id, request_id="REQ-REC-02")
    lot_bag, bal_bag = lots_svc.receive(db, lot_code="BAG-2026-001", product_id=bag.id, supplier_id=supplier.id,
                                        quantity=D("5"), unit_code="KG", unit_cost=D("11.60"),
                                        received_at=None, expiry_date=None, user_id=user.id, request_id="REQ-REC-03")
    db.flush()

    assert bal_et.on_hand_quantity == D("100.0000")
    assert bal_bah.on_hand_quantity == D("2.0000")
    assert bal_bag.on_hand_quantity == D("5.0000")

    # 3. Üretim Emri Oluştur (URT-2026-045)
    order = ProductionOrder(
        order_code="URT-2026-045",
        production_type="OUTSOURCED",
        supplier_id=supplier.id,
        status="DRAFT",
        created_by=user.id
    )
    db.add(order)
    db.flush()

    # Girdileri bağla
    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_et.id, quantity=D("100"), unit_code="KG"))
    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_bah.id, quantity=D("2"), unit_code="KG"))
    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_bag.id, quantity=D("5"), unit_code="KG"))

    # Dış fason hizmet faturası ekle (85 pk @ 5.50 € = 467.50 €)
    prod_svc.add_service_cost(
        db, order,
        ServiceCostIn(description="Dış üretim fason hizmet bedeli", quantity=D("85"), unit_price=D("5.50"))
    )

    # Başlat
    prod_svc.start(db, order, user_id=user.id)
    assert order.status == "IN_PROGRESS"

    # 4. Üretimi Tamamla (85 paket sağlam mamul)
    complete_body = CompleteIn(outputs=[
        OutputIn(product_id=sucuk.id, lot_code="SUC-2026-045", quantity=D("85"), unit_code="PACK")
    ])
    completed_order = prod_svc.complete(db, order.id, complete_body, user_id=user.id, request_id="REQ-PROD-01")

    # 5. EKP ve Maliyet Doğrulaması:
    # 100 * 9.70 (970.00) + 2 * 24.00 (48.00) + 5 * 11.60 (58.00) + 467.50 = 1543.50 €
    assert completed_order.total_cost == D("1543.5000")
    assert completed_order.actual_output_quantity == D("85.0000")

    # EKP = 1543.50 / 85 = 18.1588235... -> 4 hane: 18.1588, gösterim: 18.16
    assert completed_order.unit_cost_ekp == D("18.1588")
    assert costing.display2(completed_order.unit_cost_ekp) == D("18.16")

    # 6. Stok Düşümü Doğrulaması:
    db.refresh(bal_et)
    db.refresh(bal_bah)
    db.refresh(bal_bag)
    assert bal_et.on_hand_quantity == D("0.0000")
    assert bal_bah.on_hand_quantity == D("0.0000")
    assert bal_bag.on_hand_quantity == D("0.0000")

    # Mamul lotu oluşturulmuş ve stokta 85 paket olmalı
    sucuk_lot = db.query(Lot).filter_by(lot_code="SUC-2026-045").first()
    assert sucuk_lot is not None
    sucuk_bal = db.query(InventoryBalance).filter_by(lot_id=sucuk_lot.id).first()
    assert sucuk_bal.on_hand_quantity == D("85.0000")
    assert sucuk_lot.unit_cost == D("18.1588")


def test_lamb_butchering_weight_and_cost_distribution(db):
    user = make_user()

    supplier = Supplier(code="SUP-MEAT-01", name="Karakaya Çiftliği", supplier_type="FARM")
    db.add(supplier)

    kuzu_canli = Product(code="KUZU-CANLI", name="Bütün Kuzu Karkas", product_type="RAW_MATERIAL", base_unit_code="KG")
    but = Product(code="KUZU-BUT", name="Kuzu But", product_type="FINISHED_GOOD", base_unit_code="KG")
    sirt = Product(code="KUZU-SIRT", name="Kuzu Sırt", product_type="FINISHED_GOOD", base_unit_code="KG")
    omuz = Product(code="KUZU-OMUZ", name="Kuzu Omuz", product_type="FINISHED_GOOD", base_unit_code="KG")
    db.add_all([kuzu_canli, but, sirt, omuz])
    db.flush()

    # Karkas girişi: 25 kg @ 11.50 € ancak beyan edilen toplam tutar 351.00 € (Şartname tutarsızlığı)
    karkas_lot, karkas_bal = lots_svc.receive(
        db, lot_code="KARKAS-2026-001", product_id=kuzu_canli.id, supplier_id=supplier.id,
        quantity=D("25"), unit_code="KG", unit_cost=D("14.0400"), received_at=None,
        expiry_date=None, user_id=user.id, request_id="REQ-KARKAS-01"
    )
    db.flush()

    # Parçalama emri oluştur
    order = butch_svc.create(
        db,
        ButcheringOrder(
            order_code="PRC-2026-001",
            animal_type="KUZU",
            input_weight=D("25"),
            input_unit_code="KG",
            total_purchase_cost=D("351.00"),
            declared_unit_price=D("11.50")
        ),
        user_id=user.id
    )
    db.flush()

    # Şartname tutarsızlığı kontrolü (25 * 11.50 = 287.50 != 351.00)
    findings = butch_svc.source_findings(order)
    assert any(f.code == "SOURCE_COST_MISMATCH" for f in findings)
    mismatch = next(f for f in findings if f.code == "SOURCE_COST_MISMATCH")
    assert mismatch.details["computed_total"] == "287.5000"
    assert mismatch.details["declared_total"] == "351.00"
    assert mismatch.details["difference"] == "63.5000"

    # Girdi bağla ve başlat
    butch_svc.add_input(db, order, ButcheringInputIn(lot_id=karkas_lot.id, quantity=D("25"), unit_code="KG"))
    butch_svc.start(db, order, user_id=user.id)

    # Çıktılar: But (12 kg), Sırt (6 kg), Omuz (4 kg) = 22 kg kullanılabilir.
    # Kalan 3 kg fire/kemik için fire ekle:
    butch_svc.add_waste(db, order, WasteIn(actual_weight=D("3.0"), reason_code="BONE_WASTE", unit_code="KG",
                                           notes="Kemik ve kan kaybı tartıldı"))

    # Parçalamayı tamamla (BY_WEIGHT maliyet paylaştırma)
    complete_body = ButcheringCompleteIn(
        cost_allocation_method="BY_WEIGHT",
        outputs=[
            ButcheringOutputIn(product_id=but.id, lot_code="KUZU-BUT-001", actual_weight=D("12.0")),
            ButcheringOutputIn(product_id=sirt.id, lot_code="KUZU-SIRT-001", actual_weight=D("6.0")),
            ButcheringOutputIn(product_id=omuz.id, lot_code="KUZU-OMUZ-001", actual_weight=D("4.0")),
        ]
    )
    completed_order = butch_svc.complete(db, order.id, complete_body, user=user, request_id="REQ-BUTCH-01")

    # Maliyet denkliği doğrulaması: Parça çıktıları (308.88 €) + Fire maliyeti (42.12 €) = 351.00 €
    from app.models.butchering import ButcheringOutput, ButcheringWasteRecord
    outputs = db.query(ButcheringOutput).filter_by(butchering_order_id=completed_order.id).all()
    wastes = db.query(ButcheringWasteRecord).filter_by(butchering_order_id=completed_order.id).all()

    out_costs = [out.allocated_cost for out in outputs]
    waste_costs = [w.allocated_cost for w in wastes]
    assert sum(out_costs) == D("308.8800")
    assert sum(waste_costs) == D("42.1200")
    assert sum(out_costs) + sum(waste_costs) == D("351.0000")

    # Karkas lot stoku 0'a düşmüş olmalı
    db.refresh(karkas_bal)
    assert karkas_bal.on_hand_quantity == D("0.0000")


def test_sales_traceability_and_recall_flow(db):
    user = make_user()

    customer_a = Customer(code="MKT-A", name="Market A", customer_type="MARKET")
    customer_b = Customer(code="MKT-B", name="Market B", customer_type="MARKET")
    db.add_all([customer_a, customer_b])

    sucuk = Product(code="FIN-SUC-TRACE", name="İzlenebilir Sucuk", product_type="FINISHED_GOOD", base_unit_code="PACK")
    db.add(sucuk)
    db.flush()

    # Liste satış fiyatı: 25.00 €
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    db.add(ProductPrice(product_id=sucuk.id, price_type="SALE", amount=D("25.00"), currency_code="EUR", unit_code="PACK", valid_from=now))
    db.flush()

    # Mamul lotu girişi yap: 100 paket
    sucuk_lot, sucuk_bal = lots_svc.receive(
        db, lot_code="SUC-TRACE-001", product_id=sucuk.id, supplier_id=None,
        quantity=D("100"), unit_code="PACK", unit_cost=D("18.16"), received_at=None,
        expiry_date=None, user_id=user.id, request_id="REQ-SUC-INIT"
    )
    db.flush()

    # Satış 1: Market A'ya 30 paket sat
    sale_in = SaleIn(
        customer_id=customer_a.id,
        lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("30"), unit_code="PACK")]
    )
    sale = sales_svc.create_sale(db, sale_in, user=user, request_id="REQ-SALE-01")
    assert sale.total_amount == D("750.0000")  # 30 * 25.00 €

    db.refresh(sucuk_bal)
    assert sucuk_bal.on_hand_quantity == D("70.0000")

    # Idempotency testi: Aynı istek tekrar geldiğinde mükerrer stok düşümü olmamalı
    class SaleResponse(BaseModel):
        sale_id: int
        status: str

    def execute_sale():
        return 201, SaleResponse(sale_id=999, status="COMPLETED")

    idem_key = str(uuid.uuid4())
    req_body = {"customer_id": customer_a.id, "lines": []}
    res1 = idemp_svc.run(db, scope="SALE_CREATE", key=idem_key, body=req_body, required=True, action=execute_sale)
    assert res1.status_code == 201
    assert "Idempotent-Replay" not in res1.headers

    # İkinci çağrı: aynı anahtar ile replay yapılmalı
    res2 = idemp_svc.run(db, scope="SALE_CREATE", key=idem_key, body=req_body, required=True, action=execute_sale)
    assert res2.status_code == 201
    assert res2.headers.get("Idempotent-Replay") == "true"

    # Geri Çağırma (Recall) Başlat ve Aktifleştir
    recall_obj = recall_svc.create(
        db,
        recall_code="REC-2026-001",
        reason_code="MICROBIOLOGICAL",
        reason_text="Rutin mikrobiyolojik kontrolde listeria riski",
        lot_codes=["SUC-TRACE-001"],
        user_id=user.id
    )
    recall_svc.activate(db, recall_obj.id, user_id=user.id, request_id="REQ-ACT-01")
    db.flush()

    # Lotun durumu BLOCKED / RECALLED olmalı
    db.refresh(sucuk_lot)
    assert stock_svc.active_block(db, sucuk_lot.id) is not None

    # Bloke lotun tekrar satılması kesinlikle ENGELLENMELİ (AppError / LOT_BLOCKED)
    sale_blocked_in = SaleIn(
        customer_id=customer_b.id,
        lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("10"), unit_code="PACK")]
    )
    with pytest.raises(AppError) as exc_info:
        sales_svc.create_sale(db, sale_blocked_in, user=user, request_id="REQ-SALE-02")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "LOT_BLOCKED"

    # Simülasyonda veya etkilenen müşteri sorgusunda Market A 30 paket ile listelenmeli
    affected = recall_svc.simulate(db, recall_obj)
    assert any(c.customer_code == "MKT-A" and c.total_quantity == D("30.0000")
               for c in affected.customers)


def test_unauthorized_price_tampering_is_rejected(db):
    """Güvenlik Regresyon Testi: Yetkisiz kullanıcının liste fiyatını ezmeye çalışması engellenmelidir."""
    # SALES rolünün standart yetkileri (sales:override_price YOK)
    sales_rep = make_user(
        uid=2,
        role="SALES",
        perms={"sales:create", "sales:read", "catalog:read", "lots:read"}
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    customer = Customer(code="MKT-SEC-01", name="Market Güvenlik", customer_type="MARKET")
    sucuk = Product(code="FIN-SUC-SEC", name="Güvenlik Sucuk", product_type="FINISHED_GOOD", base_unit_code="PACK")
    db.add_all([customer, sucuk])
    db.flush()

    # Liste fiyatı: 25.00 €
    db.add(ProductPrice(product_id=sucuk.id, price_type="SALE", amount=D("25.00"), currency_code="EUR", unit_code="PACK", valid_from=now))
    db.flush()

    lot, bal = lots_svc.receive(
        db, lot_code="SUC-SEC-001", product_id=sucuk.id, supplier_id=None,
        quantity=D("50"), unit_code="PACK", unit_cost=D("18.16"), received_at=None,
        expiry_date=None, user_id=sales_rep.id, request_id="REQ-SEC-01"
    )
    db.flush()

    # Kötü niyetli/manipüle istek: Liste fiyatı 25 € olan ürünü 10 € birim fiyattan satmaya çalışıyor
    tampered_sale_in = SaleIn(
        customer_id=customer.id,
        lines=[SaleLineIn(
            lot_id=lot.id,
            quantity=D("5"),
            unit_code="PACK",
            unit_price=D("10.00")  # Yetkisiz fiyat manipülasyonu
        )]
    )

    with pytest.raises(AppError) as exc_info:
        sales_svc.create_sale(db, tampered_sale_in, user=sales_rep, request_id="REQ-SEC-02")
    assert exc_info.value.status_code == 400
    assert "yetkiniz yok" in exc_info.value.message.lower()


def test_idempotency_key_reused_with_different_body_fails_with_409(db):
    """Güvenlik Regresyon Testi: Aynı Idempotency-Key farklı gövdeyle tekrar kullanılırsa 409 dönmelidir."""
    class SimpleResp(BaseModel):
        msg: str

    def action():
        return 200, SimpleResp(msg="OK")

    idem_key = str(uuid.uuid4())
    body_initial = {"order_id": 100, "qty": 10}
    body_tampered = {"order_id": 100, "qty": 999}  # Farklı gövde

    # İlk istek başarılı
    res1 = idemp_svc.run(db, scope="TEST_SCOPE", key=idem_key, body=body_initial, required=True, action=action)
    assert res1.status_code == 200

    # Farklı gövdeyle ikinci istek: 409 IDEMPOTENCY_KEY_REUSED fırlatmalı
    with pytest.raises(AppError) as exc_info:
        idemp_svc.run(db, scope="TEST_SCOPE", key=idem_key, body=body_tampered, required=True, action=action)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "IDEMPOTENCY_KEY_REUSED"


def test_negative_quantity_receipt_rejected(db):
    """Veri Bütünlüğü Regresyon Testi: Negatif veya sıfır miktar girişi reddedilmelidir."""
    user = make_user()
    prod = Product(code="RAW-NEG-01", name="Negatif Test", product_type="RAW_MATERIAL", base_unit_code="KG")
    db.add(prod)
    db.flush()

    with pytest.raises(AppError) as exc_info:
        lots_svc.receive(
            db, lot_code="NEG-LOT-001", product_id=prod.id, supplier_id=None,
            quantity=D("-10"), unit_code="KG", unit_cost=D("5.00"), received_at=None,
            expiry_date=None, user_id=user.id, request_id="REQ-NEG-01"
        )
    assert exc_info.value.status_code == 400


def test_reference_scenario_full_traceability_and_multi_market_recall(db):
    """Şartname Referans Senaryosu:
    1. ET-2026-001 (100 kg), BAH-2026-001 (2 kg), BAG-2026-001 (5 kg) girişi
    2. URT-2026-045 üretim emri (85 pk @ 5.50 € fason hizmet bedeli)
    3. EKP hesaplama: 1.543,50 € / 85 = 18.1588 -> 18.16 €/pk mamul SUC-2026-045
    4. Market A: 30 pk, Market B: 25 pk, Market C: 30 pk (Toplam: 85 pk sevk, bakiye: 0 pk)
    5. İleriye izleme (forward): ET-2026-001 -> URT-2026-045 -> SUC-2026-045 -> Market A, B, C
    6. Geriye izleme (backward): SUC-2026-045 -> URT-2026-045 -> ET-2026-001 vb.
    7. Geri çağırma (recall): SUC-2026-045 bloke edilir (409 LOT_BLOCKED), etki simülasyonu Market A(30), B(25), C(30).
    """
    user = make_user()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Tedarikçi ve Müşteriler
    sup = Supplier(code="SUP-REF-01", name="Karakaya Besicilik", supplier_type="FARM")
    mkt_a = Customer(code="MKT-A-REF", name="Market A", customer_type="MARKET")
    mkt_b = Customer(code="MKT-B-REF", name="Market B", customer_type="MARKET")
    mkt_c = Customer(code="MKT-C-REF", name="Market C", customer_type="MARKET")
    db.add_all([sup, mkt_a, mkt_b, mkt_c])

    # Ürünler
    et = Product(code="RAW-ET-REF", name="Dana Eti", product_type="RAW_MATERIAL", base_unit_code="KG")
    bah = Product(code="RAW-BAH-REF", name="Baharat", product_type="RAW_MATERIAL", base_unit_code="KG")
    bag = Product(code="RAW-BAG-REF", name="Bağırsak", product_type="RAW_MATERIAL", base_unit_code="KG")
    sucuk = Product(code="FIN-SUC-REF", name="Kangal Sucuk", product_type="FINISHED_GOOD", base_unit_code="PACK")
    db.add_all([et, bah, bag, sucuk])
    db.flush()

    # Liste satış fiyatı: 26.00 €
    db.add(ProductPrice(product_id=sucuk.id, price_type="SALE", amount=D("26.00"), currency_code="EUR", unit_code="PACK", valid_from=now))
    db.flush()

    # 1. Hammadde Alış Girişleri
    lot_et, bal_et = lots_svc.receive(db, lot_code="ET-2026-001-REF", product_id=et.id, supplier_id=sup.id,
                                      quantity=D("100"), unit_code="KG", unit_cost=D("9.70"),
                                      received_at=None, expiry_date=None, user_id=user.id, request_id="R1")
    lot_bah, bal_bah = lots_svc.receive(db, lot_code="BAH-2026-001-REF", product_id=bah.id, supplier_id=sup.id,
                                        quantity=D("2"), unit_code="KG", unit_cost=D("24.00"),
                                        received_at=None, expiry_date=None, user_id=user.id, request_id="R2")
    lot_bag, bal_bag = lots_svc.receive(db, lot_code="BAG-2026-001-REF", product_id=bag.id, supplier_id=sup.id,
                                        quantity=D("5"), unit_code="KG", unit_cost=D("11.60"),
                                        received_at=None, expiry_date=None, user_id=user.id, request_id="R3")
    db.flush()

    # 2. Üretim Emri (URT-2026-045-REF)
    order = ProductionOrder(order_code="URT-2026-045-REF", production_type="OUTSOURCED",
                            supplier_id=sup.id, status="DRAFT", created_by=user.id)
    db.add(order)
    db.flush()

    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_et.id, quantity=D("100"), unit_code="KG"))
    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_bah.id, quantity=D("2"), unit_code="KG"))
    prod_svc.add_input(db, order, ProductionInputIn(lot_id=lot_bag.id, quantity=D("5"), unit_code="KG"))
    prod_svc.add_service_cost(db, order, ServiceCostIn(description="Fason üretim faturası", quantity=D("85"), unit_price=D("5.50")))
    prod_svc.start(db, order, user_id=user.id)

    # 3. Üretimi Tamamla (85 paket SUC-2026-045-REF)
    completed_order = prod_svc.complete(
        db, order.id,
        CompleteIn(outputs=[OutputIn(product_id=sucuk.id, lot_code="SUC-2026-045-REF", quantity=D("85"), unit_code="PACK")]),
        user_id=user.id, request_id="R4"
    )
    assert completed_order.total_cost == D("1543.5000")
    assert completed_order.unit_cost_ekp == D("18.1588")

    sucuk_lot = db.query(Lot).filter_by(lot_code="SUC-2026-045-REF").first()
    sucuk_bal = db.query(InventoryBalance).filter_by(lot_id=sucuk_lot.id).first()
    assert sucuk_bal.on_hand_quantity == D("85.0000")

    # 4. Satış ve Sevkiyatlar: Market A (30 pk), Market B (25 pk), Market C (30 pk) = 85 pk
    sale_a = sales_svc.create_sale(db, SaleIn(customer_id=mkt_a.id, lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("30"), unit_code="PACK")]), user=user, request_id="S-A")
    sale_b = sales_svc.create_sale(db, SaleIn(customer_id=mkt_b.id, lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("25"), unit_code="PACK")]), user=user, request_id="S-B")
    sale_c = sales_svc.create_sale(db, SaleIn(customer_id=mkt_c.id, lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("30"), unit_code="PACK")]), user=user, request_id="S-C")

    db.refresh(sucuk_bal)
    assert sucuk_bal.on_hand_quantity == D("0.0000")

    # 5. İleriye İzleme (Forward Trace): Hammadde lotundan başla
    fwd = trace_svc.forward(db, [lot_et.id])
    assert any(n.lot_code == "SUC-2026-045-REF" for n in fwd.lots)
    cust_map = {c.customer_code: c.total_quantity for c in fwd.customers}
    assert cust_map.get("MKT-A-REF") == D("30.0000")
    assert cust_map.get("MKT-B-REF") == D("25.0000")
    assert cust_map.get("MKT-C-REF") == D("30.0000")
    assert fwd.remaining_stock_total == D("0.0000")

    # 6. Geriye İzleme (Backward Trace): Mamul lotundan başla
    bwd = trace_svc.backward(db, sucuk_lot.id)
    assert bwd.target_lot_code == "SUC-2026-045-REF"
    ancestor_codes = {n.lot_code for n in bwd.lots}
    assert "ET-2026-001-REF" in ancestor_codes
    assert "BAH-2026-001-REF" in ancestor_codes
    assert "BAG-2026-001-REF" in ancestor_codes

    # 7. Geri Çağırma (Recall) ve Bloke Satış Engeli
    recall_obj = recall_svc.create(db, recall_code="REC-REF-001", reason_code="MICROBIOLOGICAL",
                                   reason_text="Hammadde kaynaklı kontaminasyon", lot_codes=["SUC-2026-045-REF"],
                                   user_id=user.id)
    recall_svc.activate(db, recall_obj.id, user_id=user.id, request_id="ACT-01")

    # Bloke lotun tekrar satılması 409 LOT_BLOCKED ile engellenmeli
    with pytest.raises(AppError) as exc_info:
        sales_svc.create_sale(db, SaleIn(customer_id=mkt_a.id, lines=[SaleLineIn(lot_id=sucuk_lot.id, quantity=D("1"), unit_code="PACK")]), user=user, request_id="BLOCK-TEST")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "LOT_BLOCKED"

    # Simülasyonda 3 market de görünmeli
    sim = recall_svc.simulate(db, recall_obj)
    sim_custs = {c.customer_code: c.total_quantity for c in sim.customers}
    assert sim_custs.get("MKT-A-REF") == D("30.0000")
    assert sim_custs.get("MKT-B-REF") == D("25.0000")
    assert sim_custs.get("MKT-C-REF") == D("30.0000")


def test_unauthorized_user_cost_redaction():
    """Güvenlik Doğrulaması: costs:read izni olmayan kullanıcılara maliyet ve kâr verileri maskelenmelidir."""
    payload = {
        "id": 101,
        "lot_code": "SUC-MASK-001",
        "unit_cost": "18.1588",
        "total_cost": "1543.5000",
        "unit_cost_ekp": "18.16",
        "gross_profit_per_unit": "7.84",
        "status": "COMPLETED",
        "quantity": "85.0"
    }
    redacted = redact_cost_data(payload)
    assert "unit_cost" not in redacted
    assert "total_cost" not in redacted
    assert "unit_cost_ekp" not in redacted
    assert "gross_profit_per_unit" not in redacted
    assert redacted["id"] == 101
    assert redacted["lot_code"] == "SUC-MASK-001"
    assert redacted["status"] == "COMPLETED"
    assert redacted["quantity"] == "85.0"


def test_ml_predictions_isolated_from_financial_ledgers(db):
    """Yapay Zekâ İzolasyon Doğrulaması:
    ML tahminleri bağımsız ml_predictions tablosunda saklanır; stok ve muhasebe kayıtlarını değiştirmez.
    """
    user = make_user()
    initial_movement_count = db.query(StockMovement).count()

    pred = MlPrediction(
        prediction_type="YIELD_AND_EKP",
        model_version="ridge_v1.0.0",
        status="ACTIVE",
        input_reference_type="PRODUCTION_ORDER",
        input_reference_id=45,
        predicted_value=D("85.000000"),
        predicted_cost=D("18.1600"),
        baseline_value=D("82.000000"),
        baseline_cost=D("18.8200"),
        metric_name="MAE",
        error_value=D("0.297800"),
        limitations_note="Sentetik veriyle eğitilmiştir (is_demo=True); muhasebe EKP değerinin yerine geçmez.",
        created_by=user.id
    )
    db.add(pred)
    db.flush()

    assert pred.id is not None
    # Stok hareketleri veya maliyet defterine hiçbir kayıt yazılmamış olmalı
    final_movement_count = db.query(StockMovement).count()
    assert initial_movement_count == final_movement_count
