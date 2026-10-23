"""Sentetik GEÇMİŞ veri üreteci (DEMO). Gerçek üretici verisi değildir; tüm kayıtlar is_demo=True.

Amaç: ML modellerini ve değerlendirmesini tekrarlanabilir şekilde göstermek. Dağılımlar ve gürültü
bilinçli olarak basit tutulmuştur; gerçek veriyle eğitilmedikçe performans iddiası taşımaz.
"""

import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ButcheringInput,
    ButcheringOrder,
    ButcheringOutput,
    ButcheringWasteRecord,
    Lot,
    Product,
    ProductionInput,
    ProductionOrder,
    ProductionOutput,
    ProductionServiceCost,
    Supplier,
)
from app.models.types import utcnow
from app.services import costing, stock

D = Decimal
SUPPLIERS = [("HIST-SUP-1", "Tarım Üretici A", 0.80), ("HIST-SUP-2", "Tarım Üretici B", 0.77),
             ("HIST-SUP-3", "Tarım Üretici C", 0.83)]
# hayvan türü: (ortalama ağırlık kg, ürün kodu → temel oran, alış fiyatı €/kg)
ANIMALS = {
    "KUZU": (25.0, {"BUT": 0.26, "SIRT": 0.12, "OMUZ": 0.20, "KABURGA": 0.10, "KIYMA": 0.08, "YANURUN": 0.06}, 11.5),
    "KOYUN": (45.0, {"BUT": 0.24, "SIRT": 0.11, "OMUZ": 0.18, "KABURGA": 0.11, "KIYMA": 0.10, "YANURUN": 0.07}, 9.0),
    "DANA": (220.0, {"BUT": 0.28, "SIRT": 0.14, "OMUZ": 0.16, "KABURGA": 0.09, "KIYMA": 0.12, "YANURUN": 0.05}, 10.0),
}


def _product(db: Session, code: str, name: str, ptype: str, unit: str) -> Product:
    p = db.scalar(select(Product).where(Product.code == code))
    if p is None:
        p = Product(code=code, name=name, product_type=ptype, base_unit_code=unit)
        db.add(p)
        db.flush()
    return p


def _hist_lot(db: Session, product: Product, cost: Decimal) -> Lot:
    code = f"HIST-{product.code}"
    lot = db.scalar(select(Lot).where(Lot.lot_code == code))
    if lot is None:
        lot = stock.create_lot(db, lot_code=code, product_id=product.id, quantity=D("0"), unit_code=product.base_unit_code,
                               origin="OPENING_STOCK", unit_cost=cost, is_demo=True)
        lot.status = "CLOSED"
    return lot


def generate_production(db: Session, n: int = 120, seed: int = 42) -> int:
    rnd = random.Random(seed)
    et, bah, bag = (_product(db, "ET", "Dana Eti", "RAW_MATERIAL", "KG"), _product(db, "BAHARAT", "Baharat", "RAW_MATERIAL", "KG"),
                    _product(db, "BAGIRSAK", "Bağırsak", "RAW_MATERIAL", "KG"))
    out_p = _product(db, "SUCUK", "Narin Sucuk 1 kg", "FINISHED_GOOD", "PACK")
    lots = {p.code: _hist_lot(db, p, D("1")) for p in (et, bah, bag, out_p)}
    sups = []
    for code, name, base in SUPPLIERS:
        s = db.scalar(select(Supplier).where(Supplier.code == code))
        if s is None:
            s = Supplier(code=code, name=name, supplier_type="OUTSOURCED_PROCESSOR")
            db.add(s)
            db.flush()
        sups.append((s, base))
    now = utcnow()
    existing = db.scalar(select(ProductionOrder.id).where(ProductionOrder.order_code.like("HIST-URT-%")).limit(1))
    if existing:
        return 0
    for i in range(n):
        sup, base = rnd.choice(sups)
        when = now - timedelta(days=int((n - i) * 360 / n))
        meat = round(rnd.uniform(60, 200), 1)
        spice = round(meat * rnd.uniform(0.018, 0.024), 2)
        casing = round(meat * rnd.uniform(0.04, 0.06), 2)
        total_in = meat + spice + casing
        summer = -0.012 if when.month in (6, 7, 8) else 0.0
        casing_eff = (casing / meat - 0.05) * 1.5
        y = base + summer + casing_eff + rnd.gauss(0, 0.02)
        qty = max(1, round(total_in * y))
        price_meat = round(9.2 + 1.0 * i / n + rnd.uniform(-0.15, 0.15), 2)
        svc_price = rnd.choice([D("5.00"), D("5.50"), D("5.50"), D("6.00")])
        o = ProductionOrder(order_code=f"HIST-URT-{i + 1:04d}", production_type="OUTSOURCED", status="COMPLETED",
                            supplier_id=sup.id, started_at=when, completed_at=when, created_at=when, is_demo=True)
        db.add(o)
        db.flush()
        total_input = D("0")
        for prod, q, c in ((et, meat, price_meat), (bah, spice, 24.0), (bag, casing, 11.6)):
            uc, qd = D(str(c)), D(str(q))
            tc = costing.line_total(qd, uc)
            total_input += tc
            db.add(ProductionInput(production_order_id=o.id, product_id=prod.id, lot_id=lots[prod.code].id, quantity=qd,
                                   unit_code="KG", unit_cost=uc, total_cost=tc))
        qd = D(qty)
        svc = costing.line_total(qd, svc_price)
        db.add(ProductionServiceCost(production_order_id=o.id, supplier_id=sup.id, description="Üretim hizmeti",
                                     quantity=qd, unit_price=svc_price, amount=svc, occurred_at=when))
        total = total_input + svc
        ekp = costing.unit_cost(total, qd)
        db.add(ProductionOutput(production_order_id=o.id, product_id=out_p.id, lot_id=lots[out_p.code].id, quantity=qd,
                                unit_code="PACK", unit_cost=ekp))
        o.total_input_cost, o.total_service_cost, o.total_cost = total_input, svc, total
        o.actual_output_quantity, o.unit_cost_ekp = qd, ekp
    db.flush()
    return n


def generate_butchering(db: Session, n: int = 150, seed: int = 7) -> int:
    rnd = random.Random(seed)
    if db.scalar(select(ButcheringOrder.id).where(ButcheringOrder.order_code.like("HIST-PRC-%")).limit(1)):
        return 0
    now = utcnow()
    prods: dict[tuple[str, str], Product] = {}
    for animal, (_, cuts, _) in ANIMALS.items():
        live = _product(db, f"{animal}-CANLI", f"{animal.title()} (bütün)", "RAW_MATERIAL", "KG")
        prods[(animal, "LIVE")] = live
        for cut in cuts:
            ptype = "BYPRODUCT" if cut == "YANURUN" else "FINISHED_GOOD"
            prods[(animal, cut)] = _product(db, f"{animal}-{cut}", f"{animal.title()} {cut.title()}", ptype, "KG")
    lots = {k: _hist_lot(db, p, D("1")) for k, p in prods.items()}
    animals = list(ANIMALS)
    for i in range(n):
        animal = animals[i % len(animals)]
        mean_w, cuts, price = ANIMALS[animal]
        w = round(max(mean_w * 0.6, rnd.gauss(mean_w, mean_w * 0.12)), 1)
        when = now - timedelta(days=int((n - i) * 360 / n))
        cost = costing.line_total(D(str(w)), D(str(price)))
        o = ButcheringOrder(order_code=f"HIST-PRC-{i + 1:04d}", status="COMPLETED", animal_type=animal,
                            input_weight=D(str(w)), input_unit_code="KG", total_purchase_cost=cost,
                            allocation_method="BY_WEIGHT", weight_difference=D("0"), started_at=when, completed_at=when,
                            created_at=when, is_demo=True)
        db.add(o)
        db.flush()
        db.add(ButcheringInput(butchering_order_id=o.id, lot_id=lots[(animal, "LIVE")].id,
                               product_id=prods[(animal, "LIVE")].id, quantity=o.input_weight, unit_code="KG",
                               cost_snapshot=cost))
        scale = 1 + 0.6 * (w - mean_w) / mean_w  # ağır hayvanda daha yüksek et oranı (sentetik varsayım)
        weights = {}
        for cut, base in cuts.items():
            r = max(0.005, base * scale * (1 + rnd.gauss(0, 0.06)))
            weights[cut] = D(str(round(w * r, 3)))
        out_total = sum(weights.values(), D("0"))
        waste_w = o.input_weight - out_total
        if waste_w < 0:
            factor = (o.input_weight * D("0.97")) / out_total
            weights = {k: (v * factor).quantize(D("0.001")) for k, v in weights.items()}
            out_total = sum(weights.values(), D("0"))
            waste_w = o.input_weight - out_total
        parts = costing.allocate(cost, [*weights.values(), waste_w])
        for (cut, wt), alloc in zip(weights.items(), parts[:-1], strict=True):
            db.add(ButcheringOutput(butchering_order_id=o.id, product_id=prods[(animal, cut)].id,
                                    lot_id=lots[(animal, cut)].id, output_type="BYPRODUCT" if cut == "YANURUN" else "CUT",
                                    actual_weight=wt, unit_code="KG", allocation_weight=wt, allocated_cost=alloc))
        db.add(ButcheringWasteRecord(butchering_order_id=o.id, input_lot_id=lots[(animal, "LIVE")].id,
                                     actual_weight=waste_w, unit_code="KG", reason_code="BONE_WASTE",
                                     allocated_cost=parts[-1]))
    db.flush()
    return n
