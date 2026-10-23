"""Düzeltme / ters kayıt (WF-06): tamamlanmış kayıt silinmez; kaynak bağlı ters hareket + gerekçe + audit, tek transaction.

Geri alma yalnızca çıktı lotları henüz hiç kullanılmamışsa (tam miktar yerinde, aşağı akış yok) mümkündür.
Aksi halde işlem reddedilir; zincirleme geri alma otomatik yapılmaz.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, invalid_state, not_found
from app.models import (
    ButcheringOrder,
    ButcheringOutput,
    Lot,
    LotGenealogyEdge,
    ProductionOrder,
    ProductionOutput,
    ReworkOrder,
    Sale,
    Shipment,
    ShipmentLine,
    StockMovement,
)
from app.models.types import utcnow
from app.services import audit, costing, stock

ZERO = Decimal(0)


def _movements(db: Session, source_type: str, source_id: int) -> list[StockMovement]:
    done = set(db.scalars(select(StockMovement.reverses_movement_id).where(StockMovement.reverses_movement_id.is_not(None))))
    return [m for m in db.scalars(select(StockMovement).where(StockMovement.source_type == source_type,
                                                              StockMovement.source_id == source_id).order_by(StockMovement.id))
            if m.id not in done]


def _reverse_process(db: Session, *, source_type: str, order, out_lot_ids: list[int], reason: str, user_id: int,
                     request_id: str | None, audit_action: str) -> list[int]:
    moves = _movements(db, source_type, order.id)
    locked = stock.lock_lots(db, [m.lot_id for m in moves])
    blockers = []
    for lid in out_lot_ids:
        lot, bal = locked[lid]
        used = bal.on_hand_quantity != lot.initial_quantity
        downstream = db.scalar(select(LotGenealogyEdge.id).where(LotGenealogyEdge.source_lot_id == lid).limit(1))
        shipped = db.scalar(select(ShipmentLine.id).where(ShipmentLine.lot_id == lid).limit(1))
        if used or downstream or shipped:
            blockers.append({"lot_code": lot.lot_code, "on_hand": str(bal.on_hand_quantity),
                             "initial": str(lot.initial_quantity), "has_downstream": bool(downstream or shipped)})
    if blockers:
        raise conflict("CANNOT_REVERSE", "Çıktı lotları kullanılmış; önce aşağı akış işlemleri düzeltilmelidir.",
                       {"lots": blockers})
    ids = []
    for m in moves:
        rm = stock.reverse_movement(db, m, movement_type="ADJUSTMENT", user_id=user_id,
                                    source_type=f"{source_type}_REVERSAL", source_id=order.id)
        ids.append(rm.id)
    for lid in out_lot_ids:
        locked[lid][0].status = "CLOSED"
    order.status, order.reversed_at, order.reversed_by, order.reversal_reason = "REVERSED", utcnow(), user_id, reason
    db.flush()
    audit.record(db, actor_id=user_id, action=audit_action, entity_type=source_type.lower(), entity_id=order.id,
                 request_id=request_id, details={"reason": reason, "reversal_movement_ids": ids})
    return ids


def reverse_production(db: Session, order_id: int, reason: str, user_id: int, request_id: str | None) -> ProductionOrder:
    order = db.scalar(select(ProductionOrder).where(ProductionOrder.id == order_id).with_for_update())
    if order is None:
        raise not_found("Üretim emri", order_id)
    if order.status != "COMPLETED":
        raise invalid_state("Yalnızca tamamlanmış üretim emri geri alınabilir.", {"status": order.status})
    outs = [o.lot_id for o in db.scalars(select(ProductionOutput).where(ProductionOutput.production_order_id == order.id))]
    _reverse_process(db, source_type="PRODUCTION_ORDER", order=order, out_lot_ids=outs, reason=reason,
                     user_id=user_id, request_id=request_id, audit_action="PRODUCTION_REVERSED")
    return order


def reverse_butchering(db: Session, order_id: int, reason: str, user_id: int, request_id: str | None) -> ButcheringOrder:
    order = db.scalar(select(ButcheringOrder).where(ButcheringOrder.id == order_id).with_for_update())
    if order is None:
        raise not_found("Parçalama emri", order_id)
    if order.status != "COMPLETED":
        raise invalid_state("Yalnızca tamamlanmış parçalama emri geri alınabilir.", {"status": order.status})
    outs = [o.lot_id for o in db.scalars(select(ButcheringOutput).where(ButcheringOutput.butchering_order_id == order.id))]
    _reverse_process(db, source_type="BUTCHERING_ORDER", order=order, out_lot_ids=outs, reason=reason,
                     user_id=user_id, request_id=request_id, audit_action="BUTCHERING_REVERSED")
    return order


def return_shipment(db: Session, shipment_id: int, reason: str, user_id: int, request_id: str | None) -> Shipment:
    """Müşteri iadesi: sevkiyatın tüm satırları için RETURN (IN) ters hareketi; recall kapsamından çıkar."""
    sh = db.scalar(select(Shipment).where(Shipment.id == shipment_id).with_for_update())
    if sh is None:
        raise not_found("Sevkiyat", shipment_id)
    if sh.status != "SHIPPED":
        raise invalid_state("Yalnızca sevk edilmiş sevkiyat iade alınabilir.", {"status": sh.status})
    lines = db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == sh.id)).all()
    stock.lock_lots(db, [l.lot_id for l in lines])
    for l in lines:
        stock.reverse_movement(db, db.get(StockMovement, l.stock_movement_id), movement_type="RETURN", user_id=user_id,
                               source_type="SHIPMENT_RETURN", source_id=sh.id)
    sh.status, sh.returned_at, sh.return_reason = "RETURNED", utcnow(), reason
    sale = db.scalar(select(Sale).where(Sale.shipment_id == sh.id))
    if sale is not None and sale.status == "COMPLETED":
        sale.status = "REFUNDED"
    db.flush()
    audit.record(db, actor_id=user_id, action="SHIPMENT_RETURNED", entity_type="shipment", entity_id=sh.id,
                 request_id=request_id, details={"reason": reason})
    return sh


def rework(db: Session, *, order_code: str, input_lot_id: int, input_quantity: Decimal, output_product_id: int,
           output_lot_code: str, output_quantity: Decimal, extra_cost: Decimal, reason: str, user_id: int,
           request_id: str | None) -> ReworkOrder:
    if db.scalar(select(ReworkOrder.id).where(ReworkOrder.order_code == order_code)):
        raise conflict("CONFLICT", "Yeniden işleme kodu zaten kayıtlı.", {"order_code": order_code})
    if input_quantity <= 0 or output_quantity <= 0 or extra_cost < 0:
        raise bad_request("Miktarlar pozitif, ek maliyet negatif olmayan bir değer olmalıdır.")
    if output_quantity > input_quantity:
        raise bad_request("Çıktı miktarı girdiyi aşamaz; fark kayıp olarak kabul edilir.",
                          {"input": str(input_quantity), "output": str(output_quantity)})
    src = db.get(Lot, input_lot_id)
    if src is None:
        raise not_found("Lot", input_lot_id)
    if src.unit_cost is None:
        raise bad_request("Girdi lotunun birim maliyeti kayıtlı değil.")
    locked = stock.lock_lots(db, [src.id])
    src, src_bal = locked[src.id]
    ro = ReworkOrder(order_code=order_code, input_lot_id=src.id, input_quantity=input_quantity, output_lot_id=0,
                     output_quantity=output_quantity, unit_code=src.unit_code, extra_cost=extra_cost, reason=reason,
                     created_by=user_id)
    out_cost = costing.unit_cost(costing.line_total(input_quantity, src.unit_cost) + extra_cost, output_quantity)
    out_lot = stock.create_lot(db, lot_code=output_lot_code, product_id=output_product_id, quantity=output_quantity,
                               unit_code=src.unit_code, origin="REWORK", unit_cost=out_cost, user_id=user_id,
                               supplier_id=src.supplier_id, expiry_date=src.expiry_date)
    ro.output_lot_id = out_lot.id
    db.add(ro)
    db.flush()
    stock.post_movement(db, lot=src, balance=src_bal, direction="OUT", movement_type="REWORK_ISSUE",
                        quantity=input_quantity, source_type="REWORK_ORDER", source_id=ro.id, user_id=user_id)
    out_lot, out_bal = stock.lock_lots(db, [out_lot.id])[out_lot.id]
    stock.post_movement(db, lot=out_lot, balance=out_bal, direction="IN", movement_type="REWORK_RECEIPT",
                        quantity=output_quantity, source_type="REWORK_ORDER", source_id=ro.id, user_id=user_id)
    db.add(LotGenealogyEdge(source_lot_id=src.id, target_lot_id=out_lot.id, process_type="REWORK", process_id=ro.id,
                            source_quantity=input_quantity, source_unit_code=src.unit_code,
                            target_quantity=output_quantity, target_unit_code=out_lot.unit_code))
    audit.record(db, actor_id=user_id, action="REWORK_COMPLETED", entity_type="rework_order", entity_id=ro.id,
                 request_id=request_id, details={"reason": reason, "loss": str(input_quantity - output_quantity)})
    return ro
