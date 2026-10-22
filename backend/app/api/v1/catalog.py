from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select

from app.core.deps import DB, CurrentUserDep, require
from app.core.errors import bad_request, conflict, not_found, request_id_of
from app.models import Customer, InventoryBalance, Lot, LotBlock, Product, ProductPrice, StockMovement, Supplier, Unit
from app.models.types import utcnow
from app.schemas.catalog import (AdjustmentIn, CustomerOut, LotOut, LotReceiptIn, MovementOut, PartyIn, PartyPatch,
                                 PriceIn, PriceOut, ProductIn, ProductOut, ProductPatch, SupplierOut, TransferIn, UnitOut)
from app.schemas.common import Page, PageParams, paginate
from app.services import audit, stock
from app.services import lots as lots_svc

router = APIRouter()


def get_or_404(db, model, ident, what):
    obj = db.get(model, ident)
    if obj is None:
        raise not_found(what, ident)
    return obj


PP = Annotated[PageParams, Depends()]


def lot_out(db, lot: Lot, bal: InventoryBalance | None = None, product: Product | None = None) -> LotOut:
    bal = bal or db.get(InventoryBalance, lot.id)
    product = product or db.get(Product, lot.product_id)
    return LotOut(id=lot.id, lot_code=lot.lot_code, product_id=lot.product_id, product_code=product.code,
                  product_name=product.name, supplier_id=lot.supplier_id, lot_origin_type=lot.lot_origin_type,
                  status=lot.status, unit_code=lot.unit_code, initial_quantity=lot.initial_quantity,
                  on_hand_quantity=bal.on_hand_quantity, unit_cost=lot.unit_cost, expiry_date=lot.expiry_date,
                  received_at=lot.received_at, location_code=lot.location_code,
                  is_blocked=stock.active_block(db, lot.id) is not None)


# ---- birimler / ürünler ----------------------------------------------------------------------------
@router.get("/units", response_model=list[UnitOut], tags=["catalog"])
def list_units(db: DB, _=require("catalog:read")):
    return db.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.code)).all()


@router.get("/products", response_model=Page[ProductOut], tags=["catalog"])
def list_products(db: DB, p: PP, q: str | None = None, product_type: str | None = None, _=require("catalog:read")):
    stmt = select(Product).order_by(Product.id)
    if q:
        stmt = stmt.where(or_(Product.code.ilike(f"%{q}%"), Product.name.ilike(f"%{q}%")))
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
    if p.updated_after:
        stmt = stmt.where(or_(Product.updated_at > p.updated_after, Product.created_at > p.updated_after))
    return paginate(db, stmt, p)


@router.post("/products", response_model=ProductOut, status_code=201, tags=["catalog"])
def create_product(body: ProductIn, db: DB, user=require("catalog:manage")):
    if db.get(Unit, body.base_unit_code) is None:
        raise bad_request("Bilinmeyen birim.", {"unit_code": body.base_unit_code})
    if db.scalar(select(Product.id).where(Product.code == body.code)):
        raise conflict("CONFLICT", "Ürün kodu zaten kayıtlı.", {"code": body.code})
    prod = Product(**body.model_dump())
    db.add(prod)
    db.flush()
    return prod


@router.get("/products/{product_id}", response_model=ProductOut, tags=["catalog"])
def get_product(product_id: int, db: DB, _=require("catalog:read")):
    prod = db.get(Product, product_id)
    if prod is None:
        raise not_found("Ürün", product_id)
    return prod


@router.patch("/products/{product_id}", response_model=ProductOut, tags=["catalog"])
def patch_product(product_id: int, body: ProductPatch, db: DB, _=require("catalog:manage")):
    prod = db.get(Product, product_id)
    if prod is None:
        raise not_found("Ürün", product_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(prod, k, v)
    db.flush()
    return prod


@router.post("/products/{product_id}/prices", response_model=PriceOut, status_code=201, tags=["catalog"])
def add_price(product_id: int, body: PriceIn, db: DB, user=require("catalog:manage")):
    if db.get(Product, product_id) is None:
        raise not_found("Ürün", product_id)
    now = body.valid_from or utcnow()
    prev = db.scalars(select(ProductPrice).where(ProductPrice.product_id == product_id,
                                                 ProductPrice.price_type == body.price_type,
                                                 ProductPrice.valid_to.is_(None))).all()
    for pr in prev:  # geçmiş fiyatlar korunur; yalnız aralık kapatılır
        pr.valid_to = now
    price = ProductPrice(product_id=product_id, price_type=body.price_type, amount=body.amount,
                         unit_code=body.unit_code, currency_code=body.currency_code, valid_from=now,
                         created_by=user.id)
    db.add(price)
    db.flush()
    return price


@router.get("/products/{product_id}/prices", response_model=list[PriceOut], tags=["catalog"])
def list_prices(product_id: int, db: DB, _=require("catalog:read")):
    return db.scalars(select(ProductPrice).where(ProductPrice.product_id == product_id)
                      .order_by(ProductPrice.valid_from.desc())).all()


# ---- tedarikçi / müşteri -------------------------------------------------------------------------------
@router.get("/suppliers", response_model=Page[SupplierOut], tags=["catalog"])
def list_suppliers(db: DB, p: PP, _=require("catalog:read")):
    stmt = select(Supplier).order_by(Supplier.id)
    if p.updated_after:
        stmt = stmt.where(or_(Supplier.updated_at > p.updated_after, Supplier.created_at > p.updated_after))
    return paginate(db, stmt, p)


@router.post("/suppliers", response_model=SupplierOut, status_code=201, tags=["catalog"])
def create_supplier(body: PartyIn, db: DB, _=require("catalog:manage")):
    if db.scalar(select(Supplier.id).where(Supplier.code == body.code)):
        raise conflict("CONFLICT", "Tedarikçi kodu zaten kayıtlı.")
    s = Supplier(code=body.code, name=body.name, supplier_type=body.type, phone=body.phone, email=body.email)
    db.add(s)
    db.flush()
    return s


@router.patch("/suppliers/{sid}", response_model=SupplierOut, tags=["catalog"])
def patch_supplier(sid: int, body: PartyPatch, db: DB, _=require("catalog:manage")):
    s = get_or_404(db, Supplier, sid, "Tedarikçi")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.flush()
    return s


@router.get("/customers", response_model=Page[CustomerOut], tags=["catalog"])
def list_customers(db: DB, p: PP, _=require("catalog:read")):
    stmt = select(Customer).order_by(Customer.id)
    if p.updated_after:
        stmt = stmt.where(or_(Customer.updated_at > p.updated_after, Customer.created_at > p.updated_after))
    return paginate(db, stmt, p)


@router.post("/customers", response_model=CustomerOut, status_code=201, tags=["catalog"])
def create_customer(body: PartyIn, db: DB, _=require("catalog:manage")):
    if db.scalar(select(Customer.id).where(Customer.code == body.code)):
        raise conflict("CONFLICT", "Müşteri kodu zaten kayıtlı.")
    c = Customer(code=body.code, name=body.name, customer_type=body.type, phone=body.phone, email=body.email)
    db.add(c)
    db.flush()
    return c


@router.patch("/customers/{cid}", response_model=CustomerOut, tags=["catalog"])
def patch_customer(cid: int, body: PartyPatch, db: DB, _=require("catalog:manage")):
    c = get_or_404(db, Customer, cid, "Müşteri")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.flush()
    return c


# ---- lotlar ve stok ---------------------------------------------------------------------------------------
@router.post("/lots/receipts", response_model=LotOut, status_code=201, tags=["inventory"])
def receive_lot(body: LotReceiptIn, request: Request, db: DB, user=require("lots:receive")):
    lot, bal = lots_svc.receive(db, lot_code=body.lot_code, product_id=body.product_id, supplier_id=body.supplier_id,
                                quantity=body.quantity, unit_code=body.unit_code, unit_cost=body.unit_cost,
                                received_at=body.received_at, expiry_date=body.expiry_date, user_id=user.id,
                                request_id=request_id_of(request))
    return lot_out(db, lot, bal)


@router.get("/lots", response_model=Page[LotOut], tags=["inventory"])
def list_lots(db: DB, p: PP, q: str | None = None, product_id: int | None = None, status: str | None = None,
              in_stock: bool = False, sellable: bool = False, _=require("lots:read")):
    stmt = select(Lot).join(InventoryBalance, InventoryBalance.lot_id == Lot.id).order_by(Lot.id)
    if q:
        stmt = stmt.where(Lot.lot_code.ilike(f"%{q}%"))
    if product_id:
        stmt = stmt.where(Lot.product_id == product_id)
    if status:
        stmt = stmt.where(Lot.status == status)
    if in_stock or sellable:
        stmt = stmt.where(InventoryBalance.on_hand_quantity > 0)
    if sellable:  # Android: satılabilir lotlar (aktif blokajı olmayan)
        stmt = stmt.where(~select(LotBlock.id).where(LotBlock.lot_id == Lot.id, LotBlock.unblocked_at.is_(None)).exists())
    res = paginate(db, stmt, p)
    res["items"] = [lot_out(db, lot) for lot in res["items"]]
    return res


@router.get("/lots/{lot_id}", response_model=LotOut, tags=["inventory"])
def get_lot(lot_id: int, db: DB, _=require("lots:read")):
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise not_found("Lot", lot_id)
    return lot_out(db, lot)


@router.get("/lots/by-code/{lot_code}", response_model=LotOut, tags=["inventory"])
def get_lot_by_code(lot_code: str, db: DB, _=require("lots:read")):
    lot = db.scalar(select(Lot).where(Lot.lot_code == lot_code))
    if lot is None:
        raise not_found("Lot", lot_code)
    return lot_out(db, lot)


@router.get("/inventory/movements", response_model=Page[MovementOut], tags=["inventory"])
def list_movements(db: DB, p: PP, lot_id: int | None = None, product_id: int | None = None,
                   movement_type: str | None = None, _=require("inventory:read")):
    stmt = select(StockMovement).order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
    if lot_id:
        stmt = stmt.where(StockMovement.lot_id == lot_id)
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    res = paginate(db, stmt, p)
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_({m.lot_id for m in res["items"]})))} if res["items"] else {}
    res["items"] = [MovementOut.model_validate(m).model_copy(update={"lot_code": codes.get(m.lot_id)}) for m in res["items"]]
    return res


@router.post("/inventory/adjustments", response_model=MovementOut, status_code=201, tags=["inventory"])
def adjust(body: AdjustmentIn, request: Request, db: DB, user=require("inventory:adjust")):
    locked = stock.lock_lots(db, [body.lot_id])
    lot, bal = locked[body.lot_id]
    mv = stock.post_movement(db, lot=lot, balance=bal, direction=body.direction, movement_type=body.movement_type,
                             quantity=body.quantity, source_type="ADJUSTMENT", source_id=lot.id, user_id=user.id)
    audit.record(db, actor_id=user.id, action="STOCK_ADJUSTED", entity_type="lot", entity_id=lot.id,
                 details={"reason": body.reason, "movement_id": mv.id, "direction": body.direction,
                          "quantity": str(body.quantity)}, request_id=request_id_of(request))
    return MovementOut.model_validate(mv)


@router.post("/inventory/transfers", response_model=LotOut, status_code=201, tags=["inventory"])
def transfer(body: TransferIn, request: Request, db: DB, user=require("inventory:adjust")):
    """Depo transferi: lot konumunu değiştirir; TRANSFER_OUT/TRANSFER_IN çifti ile lot bazında izlenir."""
    locked = stock.lock_lots(db, [body.lot_id])
    lot, bal = locked[body.lot_id]
    if body.quantity != bal.on_hand_quantity:
        raise bad_request("Transfer lotun tüm mevcut miktarı için yapılır.", {"on_hand": str(bal.on_hand_quantity)})
    src = lot.location_code
    stock.post_movement(db, lot=lot, balance=bal, direction="OUT", movement_type="TRANSFER_OUT",
                        quantity=body.quantity, source_type="TRANSFER", source_id=lot.id, user_id=user.id,
                        location_code=src)
    stock.post_movement(db, lot=lot, balance=bal, direction="IN", movement_type="TRANSFER_IN",
                        quantity=body.quantity, source_type="TRANSFER", source_id=lot.id, user_id=user.id,
                        location_code=body.to_location)
    lot.location_code = body.to_location
    audit.record(db, actor_id=user.id, action="LOT_TRANSFERRED", entity_type="lot", entity_id=lot.id,
                 details={"from": src, "to": body.to_location}, request_id=request_id_of(request))
    return lot_out(db, lot, bal)
