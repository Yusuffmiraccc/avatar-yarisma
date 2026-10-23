from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, invalid_state, not_found
from app.models import Lot, LotBlock, Recall, RecallCustomerImpact, RecallLot
from app.models.types import utcnow
from app.services import audit, stock, traceability

ZERO = Decimal(0)


def get_recall(db: Session, rid: int, *, lock: bool = False) -> Recall:
    stmt = select(Recall).where(Recall.id == rid)
    r = db.scalar(stmt.with_for_update() if lock else stmt)
    if r is None:
        raise not_found("Geri çağırma", rid)
    return r


def origin_lot_ids(db: Session, recall: Recall) -> list[int]:
    return list(db.scalars(select(RecallLot.lot_id).where(RecallLot.recall_id == recall.id, RecallLot.role == "ORIGIN")
                           .order_by(RecallLot.id)))


def create(db: Session, *, recall_code: str, reason_code: str, reason_text: str | None, lot_codes: list[str],
           user_id: int) -> Recall:
    if db.scalar(select(Recall.id).where(Recall.recall_code == recall_code)):
        raise conflict("CONFLICT", "Geri çağırma kodu zaten kayıtlı.", {"recall_code": recall_code})
    lots = []
    for code in dict.fromkeys(lot_codes):
        lot = db.scalar(select(Lot).where(Lot.lot_code == code))
        if lot is None:
            raise not_found("Lot", code)
        lots.append(lot)
    r = Recall(recall_code=recall_code, status="DRAFT", reason_code=reason_code, reason_text=reason_text,
               created_by=user_id)
    db.add(r)
    db.flush()
    for lot in lots:
        db.add(RecallLot(recall_id=r.id, lot_id=lot.id, role="ORIGIN"))
    db.flush()
    audit.record(db, actor_id=user_id, action="RECALL_CREATED", entity_type="recall", entity_id=r.id,
                 details={"origin_lots": lot_codes})
    return r


def simulate(db: Session, recall: Recall) -> traceability.ForwardResult:
    """Aktivasyon öncesi etki önizlemesi: hiçbir kayıt değiştirmez."""
    return traceability.forward(db, origin_lot_ids(db, recall))


def activate(db: Session, rid: int, user_id: int, request_id: str | None) -> Recall:
    """Senkron + atomik. Etkilenen tüm lotların bakiye satırları lot_id sırasıyla kilitlenir; eşzamanlı dispatch
    aynı kilidi bekler ve commit sonrası blokajı görerek LOT_BLOCKED alır."""
    recall = get_recall(db, rid, lock=True)
    if recall.status != "DRAFT":
        raise invalid_state("Yalnızca taslak geri çağırma aktifleştirilebilir.", {"status": recall.status})
    origins = origin_lot_ids(db, recall)
    # 1) kapsamı kilitsiz keşfet, 2) tüm lotları kilitle, 3) kilit altında kapsamı yeniden hesapla
    pre = traceability.forward(db, origins)
    stock.lock_lots(db, [n.lot_id for n in pre.lots])
    res = traceability.forward(db, origins)
    if {n.lot_id for n in res.lots} - {n.lot_id for n in pre.lots}:
        stock.lock_lots(db, [n.lot_id for n in res.lots])  # kilit sırasında yeni türev lot çıktıysa onları da kilitle
        res = traceability.forward(db, origins)
    now = utcnow()
    affected_ids = [node.lot_id for node in res.lots]
    existing_recall_lots = {row.lot_id: row for row in db.scalars(select(RecallLot).where(
        RecallLot.recall_id == recall.id, RecallLot.lot_id.in_(affected_ids)))}
    active_block_ids = set(db.scalars(select(LotBlock.lot_id).where(
        LotBlock.lot_id.in_(affected_ids), LotBlock.unblocked_at.is_(None))))
    for n in res.lots:
        if n.role == "DERIVED":
            db.add(RecallLot(recall_id=recall.id, lot_id=n.lot_id, role="DERIVED", blocked_at=now))
        else:
            rl = existing_recall_lots[n.lot_id]
            rl.blocked_at = now
        if n.lot_id not in active_block_ids:
            db.add(LotBlock(lot_id=n.lot_id, reason_code="RECALL", reason_text=recall.reason_text,
                            source_type="RECALL", source_id=recall.id, blocked_at=now, blocked_by=user_id))
    for h in res.shipments:
        db.add(RecallCustomerImpact(recall_id=recall.id, customer_id=h.customer_id, lot_id=h.lot_id,
                                    shipment_id=h.shipment_id, quantity=h.quantity, unit_code=h.unit_code,
                                    contact_status="PENDING"))
    recall.status, recall.started_at = "ACTIVE", now
    db.flush()
    audit.record(db, actor_id=user_id, action="RECALL_ACTIVATED", entity_type="recall", entity_id=recall.id,
                 request_id=request_id,
                 details={"blocked_lots": [n.lot_code for n in res.lots],
                          "customers": [c.customer_code for c in res.customers]})
    return recall


def resolve(db: Session, rid: int, user_id: int, request_id: str | None) -> Recall:
    recall = get_recall(db, rid, lock=True)
    if recall.status != "ACTIVE":
        raise invalid_state("Yalnızca aktif geri çağırma çözülebilir.", {"status": recall.status})
    recall.status, recall.closed_at = "RESOLVED", utcnow()  # lot blokajı KALIR (ayrı yetkili unblock gerekir)
    audit.record(db, actor_id=user_id, action="RECALL_RESOLVED", entity_type="recall", entity_id=recall.id,
                 request_id=request_id)
    return recall


def cancel(db: Session, rid: int, user_id: int) -> Recall:
    recall = get_recall(db, rid, lock=True)
    if recall.status != "DRAFT":
        raise invalid_state("Yalnızca taslak geri çağırma iptal edilebilir.", {"status": recall.status})
    recall.status = "CANCELLED"
    audit.record(db, actor_id=user_id, action="RECALL_CANCELLED", entity_type="recall", entity_id=recall.id)
    return recall


def unblock_lot(db: Session, lot_id: int, reason: str, user_id: int, request_id: str | None) -> Lot:
    lots = stock.lock_lots(db, [lot_id])
    lot, _ = lots[lot_id]
    active_recall = db.scalar(select(Recall).join(RecallLot, RecallLot.recall_id == Recall.id)
                              .where(RecallLot.lot_id == lot_id, Recall.status == "ACTIVE"))
    if active_recall is not None:
        raise conflict("RECALL_ACTIVE", "Lot aktif bir geri çağırmanın kapsamında; önce geri çağırma çözülmelidir.",
                       {"recall_code": active_recall.recall_code})
    blocks = db.scalars(select(LotBlock).where(LotBlock.lot_id == lot_id, LotBlock.unblocked_at.is_(None))).all()
    if not blocks:
        raise bad_request("Lotta aktif blokaj yok.")
    now = utcnow()
    for b in blocks:
        b.unblocked_at, b.unblocked_by, b.unblock_reason = now, user_id, reason
    audit.record(db, actor_id=user_id, action="LOT_UNBLOCKED", entity_type="lot", entity_id=lot_id,
                 request_id=request_id, details={"reason": reason, "blocks": [b.id for b in blocks]})
    return lot
