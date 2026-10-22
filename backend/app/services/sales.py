import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, invalid_state, not_found
from app.models import (Customer, Lot, Sale, SaleLine, Shipment, ShipmentLine, StockMovement)
from app.models.types import utcnow
from app.schemas.sales import SaleIn, SaleLineOut, SaleOut, ShipmentIn, ShipmentLineOut, ShipmentOut
from app.services import audit, costing, stock
from app.services.production import sale_price

ZERO = Decimal("0")


def get_shipment(db: Session, sid: int, *, lock: bool = False) -> Shipment:
    stmt = select(Shipment).where(Shipment.id == sid)
    sh = db.scalar(stmt.with_for_update() if lock else stmt)
    if sh is None:
        raise not_found("Sevkiyat", sid)
    return sh


def create_shipment(db: Session, body: ShipmentIn, user_id: int) -> Shipment:
    if db.get(Customer, body.customer_id) is None:
        raise not_found("Müşteri", body.customer_id)
    if db.scalar(select(Shipment.id).where(Shipment.shipment_code == body.shipment_code)):
        raise conflict("CONFLICT", "Sevkiyat kodu zaten kayıtlı.", {"shipment_code": body.shipment_code})
    sh = Shipment(shipment_code=body.shipment_code, customer_id=body.customer_id, status="DRAFT", notes=body.notes,
                  created_by=user_id)
    db.add(sh)
    db.flush()
    for n, l in enumerate(body.lines, 1):
        lot = db.get(Lot, l.lot_id)
        if lot is None:
            raise not_found("Lot", l.lot_id)
        if l.quantity <= 0:
            raise bad_request("Miktar pozitif olmalıdır.")
        db.add(ShipmentLine(shipment_id=sh.id, line_number=n, product_id=lot.product_id, lot_id=lot.id,
                            quantity=l.quantity, unit_code=lot.unit_code))
    db.flush()
    audit.record(db, actor_id=user_id, action="SHIPMENT_CREATED", entity_type="shipment", entity_id=sh.id)
    return sh


def dispatch(db: Session, sh: Shipment, user_id: int, request_id: str | None) -> Shipment:
    """Fiziksel stok OUT'un TEK sahibi. Satır başına tek OUT/SHIPMENT; tekrar çağrı ikinci hareket üretmez."""
    sh = get_shipment(db, sh.id, lock=True)
    if sh.status != "DRAFT":
        raise invalid_state("Yalnızca taslak sevkiyat dispatch edilebilir (tekrar dispatch yapılamaz).",
                            {"status": sh.status})
    lines = db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == sh.id)
                       .order_by(ShipmentLine.line_number)).all()
    locked = stock.lock_lots(db, [l.lot_id for l in lines])
    for l in lines:
        lot, bal = locked[l.lot_id]
        mv = stock.post_movement(db, lot=lot, balance=bal, direction="OUT", movement_type="SHIPMENT",
                                 quantity=l.quantity, source_type="SHIPMENT", source_id=sh.id, source_line_id=l.id,
                                 user_id=user_id, occurred_at=utcnow())
        l.stock_movement_id = mv.id
    sh.status, sh.shipped_at = "SHIPPED", utcnow()
    db.flush()
    audit.record(db, actor_id=user_id, action="SHIPMENT_DISPATCHED", entity_type="shipment", entity_id=sh.id,
                 request_id=request_id)
    return sh


def cancel_shipment(db: Session, sh: Shipment, user_id: int) -> None:
    if sh.status != "DRAFT":
        raise invalid_state("Yalnızca taslak sevkiyat iptal edilebilir.", {"status": sh.status})
    sh.status = "CANCELLED"  # taslak stok düşürmez
    audit.record(db, actor_id=user_id, action="SHIPMENT_CANCELLED", entity_type="shipment", entity_id=sh.id)


def shipment_out(db: Session, sh: Shipment) -> ShipmentOut:
    lines = db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == sh.id)
                       .order_by(ShipmentLine.line_number)).all()
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_([x.lot_id for x in lines])))} if lines else {}
    cust = db.get(Customer, sh.customer_id)
    out = ShipmentOut.model_validate(sh)
    out.customer_name = cust.name if cust else None
    out.lines = [ShipmentLineOut.model_validate(l).model_copy(update={"lot_code": codes.get(l.lot_id)}) for l in lines]
    return out


def create_sale(db: Session, body: SaleIn, user_id: int, request_id: str | None) -> Sale:
    """Android satışı: satış (ticari) + sevkiyat/dispatch aynı transaction'da. Başarılı yanıt = stok düştü."""
    if db.get(Customer, body.customer_id) is None:
        raise not_found("Müşteri", body.customer_id)
    code = f"SAL-{utcnow():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    sh = Shipment(shipment_code=f"SHP-{code}", customer_id=body.customer_id, status="DRAFT", created_by=user_id,
                  notes=f"Satış {code} için otomatik sevkiyat")
    db.add(sh)
    db.flush()
    sale = Sale(sale_code=code, customer_id=body.customer_id, shipment_id=sh.id, status="COMPLETED",
                sold_at=body.sold_at or utcnow(), total_amount=ZERO, created_by=user_id)
    db.add(sale)
    db.flush()
    total = ZERO
    sale_lines: list[SaleLine] = []
    for n, l in enumerate(body.lines, 1):
        lot = db.get(Lot, l.lot_id)
        if lot is None:
            raise not_found("Lot", l.lot_id)
        if l.quantity <= 0:
            raise bad_request("Miktar pozitif olmalıdır.", {"line": n})
        price = l.unit_price
        if price is None:
            pr = sale_price(db, lot.product_id)
            if pr is None:
                raise bad_request("Satır için birim fiyat verilmeli veya ürüne satış fiyatı tanımlanmalı.", {"line": n})
            price = pr.amount
        if price < 0:
            raise bad_request("Birim fiyat negatif olamaz.", {"line": n})
        lt = costing.line_total(l.quantity, price)
        total += lt
        db.add(ShipmentLine(shipment_id=sh.id, line_number=n, product_id=lot.product_id, lot_id=lot.id,
                            quantity=l.quantity, unit_code=lot.unit_code))
        sale_lines.append(SaleLine(sale_id=sale.id, line_number=n, product_id=lot.product_id, lot_id=lot.id,
                                   quantity=l.quantity, unit_code=lot.unit_code, unit_price=costing.q4(price),
                                   line_total=lt))
    db.flush()
    dispatch(db, sh, user_id, request_id)
    ship_lines = db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == sh.id)
                            .order_by(ShipmentLine.line_number)).all()
    for sl, shl in zip(sale_lines, ship_lines):
        sl.stock_movement_id = shl.stock_movement_id
        db.add(sl)
    sale.total_amount = total
    db.flush()
    audit.record(db, actor_id=user_id, action="SALE_COMPLETED", entity_type="sale", entity_id=sale.id,
                 request_id=request_id, details={"total": str(total), "shipment_id": sh.id})
    return sale


def void_sale(db: Session, sale_id: int, reason: str, user_id: int, request_id: str | None) -> Sale:
    sale = db.scalar(select(Sale).where(Sale.id == sale_id).with_for_update())
    if sale is None:
        raise not_found("Satış", sale_id)
    if sale.status != "COMPLETED":
        raise invalid_state("Yalnızca tamamlanmış satış iptal edilebilir.", {"status": sale.status})
    sh = get_shipment(db, sale.shipment_id, lock=True)
    lines = db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == sh.id)).all()
    for l in lines:  # ters hareket: kaynak kayıt korunur, silinmez
        mv = db.get(StockMovement, l.stock_movement_id)
        stock.reverse_movement(db, mv, movement_type="RETURN", user_id=user_id, source_type="SALE_VOID",
                               source_id=sale.id)
    sh.status, sale.status = "RETURNED", "VOIDED"
    db.flush()
    audit.record(db, actor_id=user_id, action="SALE_VOIDED", entity_type="sale", entity_id=sale.id,
                 request_id=request_id, details={"reason": reason})
    return sale


def sale_out(db: Session, sale: Sale) -> SaleOut:
    lines = db.scalars(select(SaleLine).where(SaleLine.sale_id == sale.id).order_by(SaleLine.line_number)).all()
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_([x.lot_id for x in lines])))} if lines else {}
    out = SaleOut.model_validate(sale)
    out.lines = [SaleLineOut.model_validate(l).model_copy(update={"lot_code": codes.get(l.lot_id)}) for l in lines]
    return out
