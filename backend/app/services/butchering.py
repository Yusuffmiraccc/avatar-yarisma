from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import CurrentUser
from app.core.errors import AppError, bad_request, conflict, invalid_state, not_found
from app.models import (ButcheringInput, ButcheringOrder, ButcheringOutput, ButcheringRecipeLine,
                        ButcheringWasteRecord, Lot, LotGenealogyEdge, Product, WeightVarianceRecord)
from app.models.types import utcnow
from app.schemas.butchering import (BInputOut, BOutputOut, ButcheringCompleteIn, ButcheringInputIn, ButcheringOrderOut,
                                    Finding, RecipeIn, RecipeLineOut, RecipeOut, VarianceOut, WasteIn, WasteOut)
from app.services import alerts, audit, costing, stock
from app.services.production import sale_price

ZERO = Decimal("0")


def get_order(db: Session, order_id: int, *, lock: bool = False) -> ButcheringOrder:
    stmt = select(ButcheringOrder).where(ButcheringOrder.id == order_id)
    order = db.scalar(stmt.with_for_update() if lock else stmt)
    if order is None:
        raise not_found("Parçalama emri", order_id)
    return order


def set_recipe(db: Session, animal_type: str, body: RecipeIn) -> RecipeOut:
    total = sum((l.expected_ratio for l in body.lines), ZERO)
    if any(l.expected_ratio < 0 or l.expected_ratio > 1 for l in body.lines) or total > 1:
        raise bad_request("Oranlar 0..1 aralığında olmalı ve toplamı 1'i aşmamalıdır.", {"ratio_sum": str(total)})
    db.execute(delete(ButcheringRecipeLine).where(ButcheringRecipeLine.animal_type == animal_type))
    for l in body.lines:
        if db.get(Product, l.product_id) is None:
            raise not_found("Ürün", l.product_id)
        db.add(ButcheringRecipeLine(animal_type=animal_type, product_id=l.product_id, output_type=l.output_type,
                                    expected_ratio=l.expected_ratio))
    db.flush()
    return get_recipe(db, animal_type)


def get_recipe(db: Session, animal_type: str) -> RecipeOut:
    rows = db.scalars(select(ButcheringRecipeLine).where(ButcheringRecipeLine.animal_type == animal_type)
                      .order_by(ButcheringRecipeLine.id)).all()
    return RecipeOut(animal_type=animal_type, lines=[RecipeLineOut.model_validate(r) for r in rows],
                     ratio_sum=sum((r.expected_ratio for r in rows), ZERO))


def create(db: Session, order: ButcheringOrder, user_id: int) -> ButcheringOrder:
    if db.scalar(select(ButcheringOrder.id).where(ButcheringOrder.order_code == order.order_code)):
        raise conflict("CONFLICT", "Parçalama emri kodu zaten kayıtlı.", {"order_code": order.order_code})
    if order.input_weight <= 0 or order.total_purchase_cost < 0:
        raise bad_request("Girdi ağırlığı pozitif, maliyet negatif olmayan değer olmalıdır.")
    order.status, order.created_by = "DRAFT", user_id
    db.add(order)
    db.flush()
    audit.record(db, actor_id=user_id, action="BUTCHERING_CREATED", entity_type="butchering_order", entity_id=order.id)
    # Kaynak belge aritmetiği: ağırlık × birim fiyat ≠ beyan edilen toplam → neden uydurmadan işaretle.
    for f in source_findings(order):
        alerts.raise_alert(db, alert_type=f.code, severity=f.severity, entity_type="butchering_order",
                           entity_id=order.id, message=f.message, details=f.details)
    return order


def source_findings(order: ButcheringOrder) -> list[Finding]:
    out: list[Finding] = []
    if order.declared_unit_price is not None:
        expected = costing.line_total(order.input_weight, order.declared_unit_price)
        if expected != order.total_purchase_cost:
            diff = order.total_purchase_cost - expected
            out.append(Finding(
                code="SOURCE_COST_MISMATCH", severity="WARNING",
                message=(f"{order.input_weight} {order.input_unit_code} × {order.declared_unit_price} = {expected}, "
                         f"ancak kayıtlı toplam alış maliyeti {order.total_purchase_cost}. Fark: {diff}. "
                         "Nedeni kaynak belgede yoktur; sistem düzeltmez, açıklama gerekir."),
                details={"computed_total": str(expected), "declared_total": str(order.total_purchase_cost),
                         "difference": str(diff)}))
    return out


def add_input(db: Session, order: ButcheringOrder, body: ButcheringInputIn) -> ButcheringInput:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Yalnızca taslak veya devam eden emre girdi eklenebilir.")
    lot = db.get(Lot, body.lot_id)
    if lot is None:
        raise not_found("Lot", body.lot_id)
    stock.require_unit(lot, body.unit_code)
    if body.unit_code != order.input_unit_code:
        raise bad_request("Girdi birimi emrin birimiyle aynı olmalıdır.")
    row = ButcheringInput(butchering_order_id=order.id, lot_id=lot.id, product_id=lot.product_id,
                          quantity=body.quantity, unit_code=lot.unit_code, cost_snapshot=ZERO)
    db.add(row)
    db.flush()
    return row


def add_waste(db: Session, order: ButcheringOrder, body: WasteIn) -> ButcheringWasteRecord:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Fire kaydı yalnızca taslak veya devam eden emre eklenebilir.")
    if body.actual_weight < 0:
        raise bad_request("Fire ağırlığı negatif olamaz.")
    if body.unit_code != order.input_unit_code:
        raise bad_request("Fire birimi emrin girdi birimiyle aynı olmalıdır.")
    inputs = db.scalars(select(ButcheringInput).where(ButcheringInput.butchering_order_id == order.id)).all()
    lot_id = body.input_lot_id
    if lot_id is None:
        if len(inputs) != 1:
            raise bad_request("Birden fazla girdi lotu varsa fire kaydı için input_lot_id zorunludur.")
        lot_id = inputs[0].lot_id
    elif lot_id not in {i.lot_id for i in inputs}:
        raise bad_request("Fire kaynağı emrin girdi lotlarından biri olmalıdır.", {"input_lot_id": lot_id})
    row = ButcheringWasteRecord(butchering_order_id=order.id, input_lot_id=lot_id, actual_weight=body.actual_weight,
                                unit_code=body.unit_code, reason_code=body.reason_code, notes=body.notes,
                                allocated_cost=ZERO)
    db.add(row)
    db.flush()
    return row


def start(db: Session, order: ButcheringOrder, user_id: int) -> None:
    if order.status != "DRAFT":
        raise invalid_state("Yalnızca taslak emir başlatılabilir.", {"status": order.status})
    inputs = db.scalars(select(ButcheringInput).where(ButcheringInput.butchering_order_id == order.id)).all()
    if not inputs:
        raise bad_request("Başlatmak için en az bir girdi lotu gerekir.")
    order.status, order.started_at = "IN_PROGRESS", utcnow()
    audit.record(db, actor_id=user_id, action="BUTCHERING_STARTED", entity_type="butchering_order", entity_id=order.id)


def cancel(db: Session, order: ButcheringOrder, user_id: int) -> None:
    if order.status not in ("DRAFT", "IN_PROGRESS"):
        raise invalid_state("Tamamlanmış emir iptal edilemez; düzeltme/ters kayıt kullanın.")
    order.status = "CANCELLED"
    audit.record(db, actor_id=user_id, action="BUTCHERING_CANCELLED", entity_type="butchering_order", entity_id=order.id)


def complete(db: Session, order_id: int, body: ButcheringCompleteIn, user: CurrentUser, request_id: str | None):
    order = get_order(db, order_id, lock=True)
    if order.status != "IN_PROGRESS":
        raise invalid_state("Yalnızca devam eden emir tamamlanabilir.", {"status": order.status})
    unit = order.input_unit_code
    inputs = db.scalars(select(ButcheringInput).where(ButcheringInput.butchering_order_id == order.id)
                        .order_by(ButcheringInput.id)).all()
    wastes = db.scalars(select(ButcheringWasteRecord).where(ButcheringWasteRecord.butchering_order_id == order.id)
                        .order_by(ButcheringWasteRecord.id)).all()
    if any(o.unit_code != unit for o in body.outputs):
        raise bad_request("Çıktı birimleri girdi birimiyle aynı olmalıdır; örtük dönüşüm yoktur.")
    if any(o.actual_weight <= 0 for o in body.outputs):
        raise bad_request("Çıktı ağırlıkları pozitif olmalıdır.")
    in_total = sum((i.quantity for i in inputs), ZERO)
    if in_total != order.input_weight:
        raise bad_request("Girdi lotlarının toplamı emrin girdi ağırlığına eşit olmalıdır.",
                          {"inputs_total": str(in_total), "order_input_weight": str(order.input_weight)})
    out_total = sum((o.actual_weight for o in body.outputs), ZERO)
    waste_total = sum((w.actual_weight for w in wastes), ZERO)
    diff = in_total - (out_total + waste_total)  # >0: açıklanamayan kayıp, <0: çıktı fazlası
    tolerance = Decimal(get_settings().weight_tolerance_kg)

    variance = None
    if abs(diff) > tolerance:
        if not body.variance_reason:
            raise conflict("WEIGHT_VARIANCE_EXCEEDED", "Ağırlık dengesi toleransı aşıldı; gerekçeli yetkili onay gerekir.", {
                "input_weight": str(in_total), "outputs_weight": str(out_total), "waste_weight": str(waste_total),
                "difference": str(diff), "tolerance": str(tolerance)})
        if "butchering:approve_variance" not in user.permissions:
            raise AppError(403, "FORBIDDEN", "Ağırlık farkını onaylama yetkiniz yok.",
                           {"required": "butchering:approve_variance"})

    loss = diff if diff > 0 else ZERO
    # --- dağıtım ---
    total_cost = order.total_purchase_cost
    rows = [("OUT", o) for o in body.outputs] + [("WASTE", w) for w in wastes] + ([("VAR", None)] if loss > 0 else [])
    if order.allocation_method == "BY_WEIGHT":
        weights = [o.actual_weight for o in body.outputs] + [w.actual_weight for w in wastes] + ([loss] if loss > 0 else [])
        values = [None] * len(rows)
    else:  # BY_VALUE
        prices = []
        for o in body.outputs:
            pr = sale_price(db, o.product_id)
            if pr is None:
                raise conflict("BY_VALUE_PRICE_MISSING", "BY_VALUE için çıktı ürününün satış fiyatı tanımlı olmalıdır.",
                               {"product_id": o.product_id})
            prices.append(pr.amount)
        if (waste_total > 0 or loss > 0) and body.waste_unit_value is None:
            raise conflict("BY_VALUE_WASTE_VALUATION_REQUIRED",
                           "BY_VALUE için onaylı fire birim değeri (waste_unit_value) olmadan tamamlanamaz.")
        wv = body.waste_unit_value or ZERO
        values = [costing.q4(o.actual_weight * p) for o, p in zip(body.outputs, prices)] \
            + [costing.q4(w.actual_weight * wv) for w in wastes] + ([costing.q4(loss * wv)] if loss > 0 else [])
        weights = values
        if sum(weights, ZERO) <= 0:
            raise bad_request("BY_VALUE toplam değeri pozitif olmalıdır.")
    parts = costing.allocate(total_cost, weights)
    assert sum(parts, ZERO) == costing.q4(total_cost)

    # --- stok: girdi OUT ---
    locked = stock.lock_lots(db, [i.lot_id for i in inputs])
    for i in inputs:
        lot, bal = locked[i.lot_id]
        stock.post_movement(db, lot=lot, balance=bal, direction="OUT", movement_type="BUTCHERING_INPUT",
                            quantity=i.quantity, source_type="BUTCHERING_ORDER", source_id=order.id,
                            source_line_id=i.id, user_id=user.id)
        i.cost_snapshot = costing.allocate(total_cost, [x.quantity for x in inputs])[inputs.index(i)]

    recipe = {r.product_id: r for r in db.scalars(select(ButcheringRecipeLine).where(
        ButcheringRecipeLine.animal_type == order.animal_type, ButcheringRecipeLine.output_type != "WASTE"))}
    out_rows: list[tuple[ButcheringOutput, Lot]] = []
    for idx, o in enumerate(body.outputs):
        alloc = parts[idx]
        lot = stock.create_lot(db, lot_code=o.lot_code, product_id=o.product_id, quantity=o.actual_weight,
                               unit_code=o.unit_code, origin="BUTCHERING", expiry_date=o.expiry_date,
                               unit_cost=costing.unit_cost(alloc, o.actual_weight), user_id=user.id)
        lot, bal = stock.lock_lots(db, [lot.id])[lot.id]
        stock.post_movement(db, lot=lot, balance=bal, direction="IN", movement_type="BUTCHERING_OUTPUT",
                            quantity=o.actual_weight, source_type="BUTCHERING_ORDER", source_id=order.id,
                            user_id=user.id)
        rl = recipe.get(o.product_id)
        row = ButcheringOutput(butchering_order_id=order.id, product_id=o.product_id, lot_id=lot.id,
                               output_type=o.output_type, actual_weight=o.actual_weight, unit_code=o.unit_code,
                               expected_weight=costing.q6(order.input_weight * rl.expected_ratio) if rl else None,
                               allocation_weight=o.actual_weight if order.allocation_method == "BY_WEIGHT" else None,
                               allocation_value=values[idx], allocated_cost=alloc)
        db.add(row)
        out_rows.append((row, lot))
    for k, w in enumerate(wastes):
        w.allocated_cost = parts[len(body.outputs) + k]  # fire: stok girişi/lot YOK
    if loss > 0:
        variance = WeightVarianceRecord(butchering_order_id=order.id, variance_weight=diff, tolerance_weight=tolerance,
                                        reason_text=body.variance_reason or "", allocated_cost=parts[-1],
                                        approved_by=user.id)
        db.add(variance)
    elif abs(diff) > tolerance:  # çıktı fazlası: maliyet payı yok, yine de gerekçeli kayıt
        variance = WeightVarianceRecord(butchering_order_id=order.id, variance_weight=diff, tolerance_weight=tolerance,
                                        reason_text=body.variance_reason or "", allocated_cost=ZERO, approved_by=user.id)
        db.add(variance)

    # --- genealogy ---
    out_w = [o.actual_weight for o in body.outputs]
    for ii, inp in enumerate(inputs):
        src_parts = costing.allocate_quantity(inp.quantity, out_w)
        for jj, (row, lot) in enumerate(out_rows):
            tgt = costing.allocate_quantity(row.actual_weight, [x.quantity for x in inputs])[ii]
            db.add(LotGenealogyEdge(source_lot_id=inp.lot_id, target_lot_id=lot.id, process_type="BUTCHERING",
                                    process_id=order.id, source_quantity=src_parts[jj], source_unit_code=inp.unit_code,
                                    target_quantity=tgt, target_unit_code=lot.unit_code))
    order.weight_difference, order.status, order.completed_at = diff, "COMPLETED", utcnow()
    db.flush()
    audit.record(db, actor_id=user.id, action="BUTCHERING_COMPLETED", entity_type="butchering_order",
                 entity_id=order.id, request_id=request_id,
                 details={"difference": str(diff), "variance_reason": body.variance_reason,
                          "allocation_method": order.allocation_method, "total_cost": str(total_cost)})
    if diff != 0:
        alerts.raise_alert(db, alert_type="WEIGHT_BALANCE_DIFFERENCE", severity="WARNING",
                           entity_type="butchering_order", entity_id=order.id,
                           message=f"Ağırlık dengesi farkı {diff} {unit}: girdi {in_total}, çıktı {out_total}, fire {waste_total}.",
                           details={"difference": str(diff), "reason": body.variance_reason})
    return order


def to_out(db: Session, order: ButcheringOrder) -> ButcheringOrderOut:
    inputs = db.scalars(select(ButcheringInput).where(ButcheringInput.butchering_order_id == order.id)
                        .order_by(ButcheringInput.id)).all()
    outputs = db.scalars(select(ButcheringOutput).where(ButcheringOutput.butchering_order_id == order.id)
                         .order_by(ButcheringOutput.id)).all()
    wastes = db.scalars(select(ButcheringWasteRecord).where(ButcheringWasteRecord.butchering_order_id == order.id)
                        .order_by(ButcheringWasteRecord.id)).all()
    var = db.scalar(select(WeightVarianceRecord).where(WeightVarianceRecord.butchering_order_id == order.id))
    lot_ids = [i.lot_id for i in inputs] + [o.lot_id for o in outputs]
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_(lot_ids)))} if lot_ids else {}
    res = ButcheringOrderOut.model_validate(order)
    res.inputs = [BInputOut.model_validate(i).model_copy(update={"lot_code": codes.get(i.lot_id)}) for i in inputs]
    res.outputs = [BOutputOut.model_validate(o).model_copy(update={
        "lot_code": codes.get(o.lot_id),
        "deviation_weight": (o.actual_weight - o.expected_weight) if o.expected_weight is not None else None,
        "unit_cost": costing.unit_cost(o.allocated_cost, o.actual_weight) if o.actual_weight > 0 else None})
        for o in outputs]
    res.waste_records = [WasteOut.model_validate(w) for w in wastes]
    res.variance = VarianceOut.model_validate(var) if var else None
    findings = source_findings(order)
    if order.status == "COMPLETED" and order.weight_difference not in (None, ZERO):
        in_total = sum((i.quantity for i in inputs), ZERO)
        findings.append(Finding(code="WEIGHT_BALANCE_DIFFERENCE", severity="WARNING",
                                message=f"Girdi {in_total} {order.input_unit_code}; çıktı+fire farkı {order.weight_difference}.",
                                details={"difference": str(order.weight_difference),
                                         "reason": var.reason_text if var else None}))
    res.findings = findings
    if order.status == "COMPLETED":
        res.sellable_cost_total = sum((o.allocated_cost for o in outputs), ZERO)
        res.waste_cost_total = sum((w.allocated_cost for w in wastes), ZERO) + (var.allocated_cost if var else ZERO)
        res.allocated_total = res.sellable_cost_total + res.waste_cost_total
    return res
