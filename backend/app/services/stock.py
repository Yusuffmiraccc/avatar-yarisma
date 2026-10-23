"""Stok defteri (append-only) + bakiye. Hareket ve bakiye aynı transaction'da yazılır.

Kilit sırası (deadlock önleme): bakiye satırları lot_id artan sırada kilitlenir.
Recall aktivasyonu ve dispatch aynı sırayı kullanır; READ COMMITTED sayesinde kilit alındıktan sonra
okunan blokajlar en güncel commit'li durumdur.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, not_found
from app.models import InventoryBalance, Lot, LotBlock, StockMovement
from app.models.types import utcnow

ZERO = Decimal(0)
# Bloke lotta da yapılabilen hareketler (imha, düzeltme, iade).
BLOCKED_OK = {"ADJUSTMENT", "WASTE", "RETURN"}


def lock_lots(db: Session, lot_ids) -> dict[int, tuple[Lot, InventoryBalance]]:
    """Lot + bakiye satırlarını lot_id sırasıyla kilitler."""
    out: dict[int, tuple[Lot, InventoryBalance]] = {}
    for lid in sorted(set(lot_ids)):
        bal = db.scalar(select(InventoryBalance).where(InventoryBalance.lot_id == lid).with_for_update())
        lot = db.get(Lot, lid)
        if lot is None or bal is None:
            raise not_found("Lot", lid)
        db.refresh(lot)
        out[lid] = (lot, bal)
    return out


def active_block(db: Session, lot_id: int) -> LotBlock | None:
    return db.scalar(select(LotBlock).where(LotBlock.lot_id == lot_id, LotBlock.unblocked_at.is_(None)).limit(1))


def create_lot(db: Session, *, lot_code: str, product_id: int, quantity: Decimal, unit_code: str, origin: str,
               supplier_id: int | None = None, received_at: datetime | None = None, expiry_date=None,
               unit_cost: Decimal | None = None, user_id: int | None = None, is_demo: bool = False) -> Lot:
    from app.models import Product

    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Ürün", product_id)
    if unit_code != product.base_unit_code:
        raise bad_request("Birim ürün birimiyle uyuşmuyor; örtük dönüşüm yapılmaz.",
                          {"expected": product.base_unit_code, "given": unit_code})
    if product.requires_expiry_date and expiry_date is None:
        raise bad_request("Bu ürün için son tüketim tarihi zorunludur.", {"field": "expiry_date"})
    if db.scalar(select(Lot.id).where(Lot.lot_code == lot_code)):
        raise conflict("CONFLICT", "Bu lot kodu zaten kayıtlı.", {"lot_code": lot_code})
    lot = Lot(lot_code=lot_code, product_id=product_id, supplier_id=supplier_id, received_at=received_at or utcnow(),
              expiry_date=expiry_date, initial_quantity=quantity, unit_code=unit_code, lot_origin_type=origin,
              status="ACTIVE", unit_cost=unit_cost, created_by=user_id, is_demo=is_demo)
    db.add(lot)
    db.flush()
    db.add(InventoryBalance(lot_id=lot.id, on_hand_quantity=ZERO, reserved_quantity=ZERO))
    db.flush()
    return lot


def post_movement(db: Session, *, lot: Lot, balance: InventoryBalance, direction: str, movement_type: str,
                  quantity: Decimal, source_type: str, source_id: int, source_line_id: int | None = None,
                  occurred_at: datetime | None = None, user_id: int | None = None, location_code: str | None = None,
                  idempotency_key: str | None = None, reverses_movement_id: int | None = None) -> StockMovement:
    """Çağıran, lot/bakiyeyi lock_lots ile kilitlemiş olmalıdır."""
    if quantity <= 0:
        raise bad_request("Hareket miktarı pozitif olmalıdır.", {"quantity": str(quantity)})
    if direction not in ("IN", "OUT"):
        raise bad_request("Yön IN veya OUT olmalıdır.")
    if direction == "OUT":
        if movement_type not in BLOCKED_OK and active_block(db, lot.id) is not None:
            raise conflict("LOT_BLOCKED", "Lot bloke; stok çıkışı yapılamaz.", {"lot_code": lot.lot_code})
        if balance.on_hand_quantity - balance.reserved_quantity < quantity:
            raise conflict("INSUFFICIENT_STOCK", "Yetersiz stok.",
                           {"lot_code": lot.lot_code, "available": format(balance.on_hand_quantity - balance.reserved_quantity, "f"),
                            "requested": format(quantity, "f")})
        balance.on_hand_quantity -= quantity
    else:
        balance.on_hand_quantity += quantity
    lot.status = "EXHAUSTED" if balance.on_hand_quantity == 0 else "ACTIVE"
    mv = StockMovement(product_id=lot.product_id, lot_id=lot.id, direction=direction, movement_type=movement_type,
                       quantity=quantity, unit_code=lot.unit_code, source_type=source_type, source_id=source_id,
                       source_line_id=source_line_id, location_code=location_code or lot.location_code,
                       idempotency_key=idempotency_key, reverses_movement_id=reverses_movement_id,
                       occurred_at=occurred_at or utcnow(), created_by=user_id)
    db.add(mv)
    db.flush()
    return mv


def require_unit(lot: Lot, unit_code: str) -> None:
    if lot.unit_code != unit_code:
        raise bad_request("Birim lot birimiyle uyuşmuyor; örtük birim dönüşümü yapılmaz.",
                          {"lot_unit": lot.unit_code, "given": unit_code})


def reverse_movement(db: Session, mv: StockMovement, *, movement_type: str, user_id: int | None, source_type: str,
                     source_id: int) -> StockMovement:
    lots = lock_lots(db, [mv.lot_id])
    lot, bal = lots[mv.lot_id]
    return post_movement(db, lot=lot, balance=bal, direction="IN" if mv.direction == "OUT" else "OUT",
                         movement_type=movement_type, quantity=mv.quantity, source_type=source_type,
                         source_id=source_id, user_id=user_id, reverses_movement_id=mv.id)
