from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, invalid_state, not_found
from app.core.units import MASS_TO_KG
from app.models import (
    Lot,
    LotGenealogyEdge,
    Product,
    ProductionInput,
    ProductionOrder,
    ProductionOutput,
    ProductionServiceCost,
    ProductPrice,
)
from app.models.types import utcnow
from app.schemas.production import (
    CompleteIn,
    InputOut,
    OutputOut,
    ProductionInputIn,
    ProductionOrderOut,
    ServiceCostIn,
    ServiceCostOut,
)
from app.services import audit, costing, stock

ZERO = Decimal(0)


def get_order(db: Session, order_id: int, *, lock: bool = False) -> ProductionOrder:
    stmt = select(ProductionOrder).where(ProductionOrder.id == order_id)
    order = db.scalar(stmt.with_for_update() if lock else stmt)
    if order is None:
        raise not_found("Üretim emri", order_id)
    return order


def add_input(db: Session, order: ProductionOrder, body: ProductionInputIn) -> ProductionInput:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Yalnızca taslak veya devam eden emre girdi eklenebilir.", {"status": order.status})
    lot = db.get(Lot, body.lot_id)
    if lot is None:
        raise not_found("Lot", body.lot_id)
    stock.require_unit(lot, body.unit_code)
    if body.quantity <= 0:
        raise bad_request("Miktar pozitif olmalıdır.")
    if lot.unit_cost is None:
        raise bad_request("Lotun birim maliyeti kayıtlı değil; maliyet sunucuda lot kaydından alınır.",
                          {"lot_code": lot.lot_code})
    inp = ProductionInput(production_order_id=order.id, product_id=lot.product_id, lot_id=lot.id,
                          quantity=body.quantity, unit_code=lot.unit_code, unit_cost=lot.unit_cost,
                          total_cost=costing.line_total(body.quantity, lot.unit_cost))
    db.add(inp)
    db.flush()
    return inp


def add_service_cost(db: Session, order: ProductionOrder, body: ServiceCostIn) -> ProductionServiceCost:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Yalnızca taslak veya devam eden emre hizmet maliyeti eklenebilir.")
    if body.quantity is not None and body.unit_price is not None:
        amount = costing.line_total(body.quantity, body.unit_price)
        if body.amount is not None and costing.q4(body.amount) != amount:
            raise bad_request("amount, quantity × unit_price ile uyuşmuyor.",
                              {"expected": str(amount), "given": str(body.amount)})
    elif body.amount is not None:
        amount = costing.q4(body.amount)
    else:
        raise bad_request("quantity+unit_price veya amount verilmelidir.")
    if amount < 0:
        raise bad_request("Tutar negatif olamaz.")
    row = ProductionServiceCost(production_order_id=order.id, supplier_id=body.supplier_id or order.supplier_id,
                                description=body.description, quantity=body.quantity, unit_price=body.unit_price,
                                amount=amount, occurred_at=utcnow())
    db.add(row)
    db.flush()
    return row


def start(db: Session, order: ProductionOrder, user_id: int) -> None:
    if order.status != "DRAFT":
        raise invalid_state("Yalnızca taslak emir başlatılabilir.", {"status": order.status})
    order.status = "IN_PROGRESS"
    order.started_at = utcnow()
    audit.record(db, actor_id=user_id, action="PRODUCTION_STARTED", entity_type="production_order", entity_id=order.id)


def cancel(db: Session, order: ProductionOrder, user_id: int) -> None:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Tamamlanmış emir iptal edilemez; düzeltme/ters kayıt kullanın.", {"status": order.status})
    order.status = "CANCELLED"  # IN_PROGRESS stok düşürmediği için stok etkisi yoktur
    audit.record(db, actor_id=user_id, action="PRODUCTION_CANCELLED", entity_type="production_order", entity_id=order.id)


def complete(db: Session, order_id: int, body: CompleteIn, user_id: int, request_id: str | None) -> ProductionOrder:
    """Tek transaction: tüketim OUT, mamul IN, genealogy, maliyet snapshot'ı ve audit. Hata → tam rollback."""
    order = get_order(db, order_id, lock=True)
    if order.status != "IN_PROGRESS":
        raise invalid_state("Yalnızca devam eden emir tamamlanabilir.", {"status": order.status})
    inputs = db.scalars(select(ProductionInput).where(ProductionInput.production_order_id == order.id)
                        .order_by(ProductionInput.id)).all()
    if not inputs:
        raise bad_request("Tamamlamak için en az bir girdi gerekir.")
    out_units = {o.unit_code for o in body.outputs}
    if len(out_units) != 1:
        raise bad_request("Tüm çıktılar aynı birimde olmalıdır.")
    out_qty_total = sum((o.quantity for o in body.outputs), ZERO)
    if any(o.quantity <= 0 for o in body.outputs):
        raise bad_request("Çıktı miktarları pozitif olmalıdır.")

    locked = stock.lock_lots(db, [i.lot_id for i in inputs])
    for inp in inputs:
        lot, bal = locked[inp.lot_id]
        stock.post_movement(db, lot=lot, balance=bal, direction="OUT", movement_type="PRODUCTION_ISSUE",
                            quantity=inp.quantity, source_type="PRODUCTION_ORDER", source_id=order.id,
                            source_line_id=inp.id, user_id=user_id)

    services = db.scalars(select(ProductionServiceCost).where(ProductionServiceCost.production_order_id == order.id)).all()
    total_input = sum((i.total_cost for i in inputs), ZERO)
    total_service = sum((s.amount for s in services), ZERO)
    total = total_input + total_service
    ekp = costing.unit_cost(total, out_qty_total)

    out_lots: list[tuple[Lot, Decimal]] = []
    for o in body.outputs:
        prod = db.get(Product, o.product_id)
        if prod is None:
            raise not_found("Ürün", o.product_id)
        lot = stock.create_lot(db, lot_code=o.lot_code, product_id=o.product_id, quantity=o.quantity,
                               unit_code=o.unit_code, origin="PRODUCTION", expiry_date=o.expiry_date,
                               unit_cost=ekp, user_id=user_id)
        (lot, bal) = stock.lock_lots(db, [lot.id])[lot.id]
        stock.post_movement(db, lot=lot, balance=bal, direction="IN", movement_type="PRODUCTION_RECEIPT",
                            quantity=o.quantity, source_type="PRODUCTION_ORDER", source_id=order.id, user_id=user_id)
        db.add(ProductionOutput(production_order_id=order.id, product_id=o.product_id, lot_id=lot.id,
                                quantity=o.quantity, unit_code=o.unit_code, unit_cost=ekp))
        out_lots.append((lot, o.quantity))

    # Genealogy: her girdi lotu → her çıktı lotu; miktarlar toplamı koruyacak şekilde dağıtılır.
    in_w = [i.quantity for i in inputs]
    out_w = [q for _, q in out_lots]
    for ii, inp in enumerate(inputs):
        src_parts = costing.allocate_quantity(inp.quantity, out_w)
        for jj, (olot, oq) in enumerate(out_lots):
            tgt = costing.allocate_quantity(oq, in_w)[ii]
            db.add(LotGenealogyEdge(source_lot_id=inp.lot_id, target_lot_id=olot.id, process_type="PRODUCTION",
                                    process_id=order.id, source_quantity=src_parts[jj],
                                    source_unit_code=inp.unit_code, target_quantity=tgt,
                                    target_unit_code=olot.unit_code))

    order.total_input_cost, order.total_service_cost, order.total_cost = total_input, total_service, total
    order.actual_output_quantity, order.unit_cost_ekp = out_qty_total, ekp
    order.status, order.completed_at = "COMPLETED", utcnow()
    db.flush()
    audit.record(db, actor_id=user_id, action="PRODUCTION_COMPLETED", entity_type="production_order",
                 entity_id=order.id, request_id=request_id,
                 details={"total_cost": str(total), "output_quantity": str(out_qty_total), "ekp": str(ekp)})
    return order


def sale_price(db: Session, product_id: int):
    now = utcnow()
    return db.scalar(select(ProductPrice).where(ProductPrice.product_id == product_id, ProductPrice.price_type == "SALE",
                                               ProductPrice.valid_from <= now,
                                               (ProductPrice.valid_to.is_(None) | (ProductPrice.valid_to > now)))
                     .order_by(ProductPrice.valid_from.desc()).limit(1))


def to_out_many(db: Session, orders: list[ProductionOrder]) -> list[ProductionOrderOut]:
    if not orders:
        return []
    ids = [o.id for o in orders]
    inputs = db.scalars(select(ProductionInput).where(ProductionInput.production_order_id.in_(ids))
                        .order_by(ProductionInput.id)).all()
    services = db.scalars(select(ProductionServiceCost).where(ProductionServiceCost.production_order_id.in_(ids))
                          .order_by(ProductionServiceCost.id)).all()
    outputs = db.scalars(select(ProductionOutput).where(ProductionOutput.production_order_id.in_(ids))
                         .order_by(ProductionOutput.id)).all()
    lot_ids = {i.lot_id for i in inputs} | {o.lot_id for o in outputs}
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_(lot_ids)))} if lot_ids else {}
    product_ids = {o.product_id for o in outputs}
    prices = {}
    if product_ids:
        for price in db.scalars(select(ProductPrice).where(ProductPrice.product_id.in_(product_ids),
                ProductPrice.price_type == "SALE", ProductPrice.valid_from <= utcnow(),
                (ProductPrice.valid_to.is_(None) | (ProductPrice.valid_to > utcnow())))
                .order_by(ProductPrice.valid_from.desc())):
            prices.setdefault(price.product_id, price)
    by_input, by_service, by_output = {}, {}, {}
    for row in inputs:
        by_input.setdefault(row.production_order_id, []).append(row)
    for row in services:
        by_service.setdefault(row.production_order_id, []).append(row)
    for row in outputs:
        by_output.setdefault(row.production_order_id, []).append(row)
    return [_to_out(db, order, by_input.get(order.id, []), by_service.get(order.id, []),
                    by_output.get(order.id, []), codes, prices) for order in orders]


def to_out(db: Session, order: ProductionOrder) -> ProductionOrderOut:
    return to_out_many(db, [order])[0]


def _to_out(db: Session, order: ProductionOrder, inputs, services, outputs, codes, prices) -> ProductionOrderOut:
    out = ProductionOrderOut.model_validate(order)
    out.inputs = [InputOut.model_validate(i).model_copy(update={"lot_code": codes.get(i.lot_id)}) for i in inputs]
    out.service_costs = [ServiceCostOut.model_validate(s) for s in services]
    out.outputs = [OutputOut.model_validate(o).model_copy(update={"lot_code": codes.get(o.lot_id)}) for o in outputs]
    if order.actual_output_quantity is not None and order.planned_quantity is not None:
        out.quantity_difference = order.actual_output_quantity - order.planned_quantity
    mass = sum((i.quantity * MASS_TO_KG[i.unit_code] for i in inputs if i.unit_code in MASS_TO_KG), ZERO)
    if mass > 0:
        out.input_mass_kg = mass
        if order.actual_output_quantity:
            out.yield_ratio = costing.q6(order.actual_output_quantity / mass)
    if order.unit_cost_ekp is not None:
        out.unit_cost_ekp_display = costing.display2(order.unit_cost_ekp)
        if outputs:
            price = prices.get(outputs[0].product_id)
            if price is not None:
                m = costing.margin(price.amount, order.unit_cost_ekp)
                out.vkp = price.amount
                out.gross_profit_per_unit = m["gross_profit_per_unit"]
                out.margin_percent = m["margin_percent"]
                out.gross_profit_total = costing.q4(m["gross_profit_per_unit"] * order.actual_output_quantity)
    return out
