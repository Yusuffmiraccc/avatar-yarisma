"""Anomali taraması: kural + basit istatistik (z-skoru). Tahmin değil; kayıtlı verinin tutarlılık kontrolleri.

Her uyarı açıklanabilir (details) ve idempotent (aynı varlık için açık uyarı varken tekrar üretilmez).
"""

import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml import anomaly_model
from app.ml.service import butchering_frame, production_frame
from app.models import (
    AnomalyAlert,
    ButcheringOrder,
    ButcheringWasteRecord,
    InventoryBalance,
    Lot,
    LotGenealogyEdge,
    ProductionInput,
    ProductionOrder,
    StockMovement,
)
from app.services import alerts

ZERO = Decimal(0)
Z = 2.5
MIN_HISTORY = 10


def ledger_mismatches(db: Session) -> list[dict]:
    """Bakiye ≠ Σ(IN) − Σ(OUT) olan lotlar (defter bütünlüğü)."""
    signed = func.sum(func.if_(StockMovement.direction == "IN", StockMovement.quantity, -StockMovement.quantity))
    ledger = dict(db.execute(select(StockMovement.lot_id, signed).group_by(StockMovement.lot_id)).all())
    out = []
    for bal, lot in db.execute(select(InventoryBalance, Lot).join(Lot, Lot.id == InventoryBalance.lot_id)):
        expected = ledger.get(bal.lot_id, ZERO) or ZERO
        if bal.on_hand_quantity != expected:
            out.append({"lot_id": lot.id, "lot_code": lot.lot_code, "balance": str(bal.on_hand_quantity),
                        "ledger_sum": str(expected)})
    return out


def _open(db: Session, alert_type: str, entity_type: str, entity_id: int) -> bool:
    return db.scalar(select(AnomalyAlert.id).where(
        AnomalyAlert.alert_type == alert_type, AnomalyAlert.entity_type == entity_type,
        AnomalyAlert.entity_id == entity_id, AnomalyAlert.acknowledged_at.is_(None)).limit(1)) is not None


def _raise(db: Session, created: list, alert_type: str, severity: str, entity_type: str, entity_id: int, message: str,
           details: dict) -> None:
    if not _open(db, alert_type, entity_type, entity_id):
        created.append(alerts.raise_alert(db, alert_type=alert_type, severity=severity, entity_type=entity_type,
                                          entity_id=entity_id, message=message, details=details))


def _z(values: list[float], x: float) -> float | None:
    if len(values) < MIN_HISTORY:
        return None
    sd = statistics.pstdev(values)
    return (x - statistics.mean(values)) / sd if sd > 0 else None


def _multivariate(db: Session, created: list, z_flagged: set[tuple[str, int]]) -> None:
    """IsolationForest: tek tek normal görünen ama birlikte olağandışı kayıtlar (z-skoru yakalamadıklarını)."""
    pdf = production_frame(db)
    if len(pdf):
        mask, score = anomaly_model.isolation_outliers(pdf[["yield_ratio", "ekp"]].to_numpy())
        for oid, hit, s, y in zip(pdf["order_id"], mask, score, pdf["yield_ratio"], strict=True):
            if hit and ("production_order", int(oid)) not in z_flagged:
                code = db.get(ProductionOrder, int(oid)).order_code
                _raise(db, created, "MULTIVARIATE_ANOMALY", "INFO", "production_order", int(oid),
                       f"{code}: verim ve maliyet birlikte olağandışı (anomali skoru {s:.2f}).",
                       {"anomaly_score": float(s), "yield_ratio": float(y), "model": "ISOLATION_FOREST"})
    bdf, targets = butchering_frame(db)
    if len(bdf):
        cols = [f"r_{t}" for t in targets]
        for animal, g in bdf.groupby("animal_type"):
            mask, score = anomaly_model.isolation_outliers(g[cols].to_numpy())
            for oid, hit, s in zip(g["order_id"], mask, score, strict=True):
                if hit and ("butchering_order", int(oid)) not in z_flagged:
                    code = db.get(ButcheringOrder, int(oid)).order_code
                    _raise(db, created, "MULTIVARIATE_ANOMALY", "INFO", "butchering_order", int(oid),
                           f"{code}: {animal} parça oranları alışılmışın dışında (anomali skoru {s:.2f}).",
                           {"anomaly_score": float(s), "model": "ISOLATION_FOREST"})


def scan(db: Session) -> list[AnomalyAlert]:
    created: list[AnomalyAlert] = []
    for m in ledger_mismatches(db):
        _raise(db, created, "LEDGER_BALANCE_MISMATCH", "CRITICAL", "lot", m["lot_id"],
               f"{m['lot_code']}: bakiye {m['balance']} ≠ defter toplamı {m['ledger_sum']}.", m)

    orders = db.scalars(select(ProductionOrder).where(ProductionOrder.status == "COMPLETED")).all()
    yields, ekps = {}, {}
    for o in orders:
        mass = db.scalar(select(func.sum(ProductionInput.quantity)).where(
            ProductionInput.production_order_id == o.id, ProductionInput.unit_code == "KG"))
        if mass and o.actual_output_quantity:
            yields[o.id] = float(o.actual_output_quantity / mass)
        if o.unit_cost_ekp is not None:
            ekps[o.id] = float(o.unit_cost_ekp)
        if db.scalar(select(func.count()).select_from(LotGenealogyEdge).where(
                LotGenealogyEdge.process_type == "PRODUCTION", LotGenealogyEdge.process_id == o.id)) == 0 and not o.is_demo:
            _raise(db, created, "MISSING_GENEALOGY", "CRITICAL", "production_order", o.id,
                   f"{o.order_code}: tamamlanmış emirde lot genealogy kaydı yok.", {"order_code": o.order_code})
    z_flagged: set[tuple[str, int]] = set()
    for oid, y in yields.items():
        z = _z(list(yields.values()), y)
        if z is not None and z < -Z:
            z_flagged.add(("production_order", oid))
            o = next(x for x in orders if x.id == oid)
            _raise(db, created, "LOW_PRODUCTION_YIELD", "WARNING", "production_order", oid,
                   f"{o.order_code}: verim {y:.3f}, ortalamanın {abs(z):.1f} σ altında.", {"yield_ratio": y, "z": z})
    for oid, e in ekps.items():
        z = _z(list(ekps.values()), e)
        if z is not None and z > Z:
            z_flagged.add(("production_order", oid))
            o = next(x for x in orders if x.id == oid)
            _raise(db, created, "COST_INCREASE", "WARNING", "production_order", oid,
                   f"{o.order_code}: EKP {e:.4f}, ortalamanın {z:.1f} σ üzerinde.", {"ekp": e, "z": z})

    by_animal = defaultdict(list)
    for o in db.scalars(select(ButcheringOrder).where(ButcheringOrder.status == "COMPLETED")):
        waste = db.scalar(select(func.sum(ButcheringWasteRecord.actual_weight)).where(
            ButcheringWasteRecord.butchering_order_id == o.id)) or ZERO
        by_animal[o.animal_type].append((o, float(waste / o.input_weight)))
    for animal, rows in by_animal.items():
        vals = [r for _, r in rows]
        for o, r in rows:
            z = _z(vals, r)
            if z is not None and z > Z:
                z_flagged.add(("butchering_order", o.id))
                _raise(db, created, "UNEXPECTED_WASTE", "WARNING", "butchering_order", o.id,
                       f"{o.order_code}: fire oranı {r:.3f}, {animal} ortalamasının {z:.1f} σ üzerinde.",
                       {"waste_ratio": r, "z": z})

    _multivariate(db, created, z_flagged)

    soon = date.today() + timedelta(days=7)
    for lot, bal in db.execute(select(Lot, InventoryBalance).join(InventoryBalance, InventoryBalance.lot_id == Lot.id)
                               .where(Lot.expiry_date.is_not(None), Lot.expiry_date <= soon,
                                      InventoryBalance.on_hand_quantity > 0)):
        _raise(db, created, "LOT_EXPIRING", "WARNING", "lot", lot.id,
               f"{lot.lot_code}: son tüketim {lot.expiry_date}, stokta {bal.on_hand_quantity} {lot.unit_code}.",
               {"expiry_date": str(lot.expiry_date)})
    return created
