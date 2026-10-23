"""Lot kabulü (hammadde girişi). API ve onaylanan belge aynı yolu kullanır."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models import Lot, Product, Supplier
from app.services import audit, stock


def receive(db: Session, *, lot_code: str, product_id: int, supplier_id: int | None, quantity: Decimal, unit_code: str,
            unit_cost: Decimal, received_at: datetime | None, expiry_date: date | None, user_id: int,
            request_id: str | None, source: str | None = None) -> tuple[Lot, object]:
    prod = db.get(Product, product_id)
    if prod is None:
        raise not_found("Ürün", product_id)
    if quantity <= 0 or unit_cost < 0:
        raise bad_request("Miktar pozitif, birim maliyet negatif olmayan bir değer olmalıdır.")
    if supplier_id is not None and db.get(Supplier, supplier_id) is None:
        raise not_found("Tedarikçi", supplier_id)
    lot = stock.create_lot(db, lot_code=lot_code, product_id=product_id, quantity=quantity, unit_code=unit_code,
                           origin="PURCHASE", supplier_id=supplier_id, received_at=received_at, expiry_date=expiry_date,
                           unit_cost=unit_cost, user_id=user_id)
    lot, bal = stock.lock_lots(db, [lot.id])[lot.id]
    mv = stock.post_movement(db, lot=lot, balance=bal, direction="IN", movement_type="RECEIPT", quantity=quantity,
                             source_type="LOT_RECEIPT", source_id=lot.id, user_id=user_id, occurred_at=received_at)
    audit.record(db, actor_id=user_id, action="LOT_RECEIVED", entity_type="lot", entity_id=lot.id,
                 details={"lot_code": lot_code, "quantity": str(quantity), "movement_id": mv.id, "source": source},
                 request_id=request_id)
    return lot, bal
