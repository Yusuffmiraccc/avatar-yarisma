from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import DB, require
from app.core.errors import not_found
from app.models import (
    AnomalyAlert,
    Customer,
    InventoryBalance,
    Lot,
    LotBlock,
    Product,
    ProductionOrder,
    Recall,
    RecallCustomerImpact,
    Shipment,
)
from app.schemas.common import redact_cost_data
from app.services import anomaly, costing
from app.services import production as prod_svc

router = APIRouter(prefix="/reports", tags=["reports"])
ZERO = Decimal(0)


@router.get("/dashboard")
def dashboard(db: DB, _=require("reports:read")):
    value = db.scalar(select(func.sum(InventoryBalance.on_hand_quantity * Lot.unit_cost)).join(
        Lot, Lot.id == InventoryBalance.lot_id)) or ZERO
    result = {
        "stock_value": format(costing.q4(value), "f"),
        "lots_in_stock": db.scalar(select(func.count()).select_from(InventoryBalance).where(InventoryBalance.on_hand_quantity > 0)),
        "blocked_lots": db.scalar(select(func.count(func.distinct(LotBlock.lot_id))).where(LotBlock.unblocked_at.is_(None))),
        "active_recalls": db.scalar(select(func.count()).select_from(Recall).where(Recall.status == "ACTIVE")),
        "open_alerts": db.scalar(select(func.count()).select_from(AnomalyAlert).where(AnomalyAlert.acknowledged_at.is_(None))),
        "completed_production_orders": db.scalar(select(func.count()).select_from(ProductionOrder).where(ProductionOrder.status == "COMPLETED")),
        "shipments_shipped": db.scalar(select(func.count()).select_from(Shipment).where(Shipment.status == "SHIPPED")),
    }
    if "costs:read" not in _.permissions:
        result.pop("stock_value", None)
    return result


@router.get("/production-costs")
def production_costs(db: DB, _=require("reports:read")):
    rows = db.scalars(select(ProductionOrder).where(ProductionOrder.status == "COMPLETED", ProductionOrder.is_demo.is_(False))
                      .order_by(ProductionOrder.id.desc())).all()
    out = []
    for o in rows:
        r = prod_svc.to_out(db, o)
        out.append({"order_code": r.order_code, "total_input_cost": r.total_input_cost, "total_service_cost": r.total_service_cost,
                    "total_cost": r.total_cost, "output_quantity": r.actual_output_quantity, "ekp": r.unit_cost_ekp,
                    "ekp_display": r.unit_cost_ekp_display, "vkp": r.vkp, "gross_profit_per_unit": r.gross_profit_per_unit,
                    "margin_percent": r.margin_percent, "gross_profit_total": r.gross_profit_total,
                    "yield_ratio": r.yield_ratio})
    result = {"items": [{k: (format(v, "f") if isinstance(v, Decimal) else v) for k, v in x.items()} for x in out]}
    return result if "costs:read" in _.permissions else redact_cost_data(result)


@router.get("/stock-valuation")
def stock_valuation(db: DB, _=require("reports:read")):
    rows = db.execute(select(Product.code, Product.name, Lot.unit_code, func.sum(InventoryBalance.on_hand_quantity),
                             func.sum(InventoryBalance.on_hand_quantity * Lot.unit_cost))
                      .join(Lot, Lot.product_id == Product.id).join(InventoryBalance, InventoryBalance.lot_id == Lot.id)
                      .where(InventoryBalance.on_hand_quantity > 0).group_by(Product.code, Product.name, Lot.unit_code)).all()
    items = [{"product_code": c, "product_name": n, "unit_code": u, "on_hand": format(q, "f"),
              "value": format(costing.q4(v or ZERO), "f")} for c, n, u, q, v in rows]
    result = {"items": items, "total_value": format(costing.q4(sum((Decimal(i["value"]) for i in items), ZERO)), "f")}
    return result if "costs:read" in _.permissions else redact_cost_data(result)


@router.get("/ledger-integrity")
def ledger_integrity(db: DB, _=require("reports:read")):
    bad = anomaly.ledger_mismatches(db)
    return {"consistent": not bad, "mismatches": bad}


@router.get("/recalls/{recall_id}/notification-list")
def notification_list(recall_id: int, db: DB, _=require("recalls:read")):
    r = db.get(Recall, recall_id)
    if r is None:
        raise not_found("Geri çağırma", recall_id)
    rows = db.execute(select(RecallCustomerImpact, Customer, Lot).join(Customer, Customer.id == RecallCustomerImpact.customer_id)
                      .join(Lot, Lot.id == RecallCustomerImpact.lot_id).where(RecallCustomerImpact.recall_id == recall_id)
                      .order_by(Customer.code, Lot.lot_code)).all()
    return {"recall_code": r.recall_code, "status": r.status, "items": [
        {"customer_code": c.code, "customer_name": c.name, "phone": c.phone, "email": c.email, "lot_code": l.lot_code,
         "quantity": format(i.quantity, "f"), "unit_code": i.unit_code, "contact_status": i.contact_status,
         "contacted_at": i.contacted_at.isoformat() + "Z" if i.contacted_at else None} for i, c, l in rows],
        "second_tier_note": "İkinci kademe dağıtım yalnızca kayıtlıysa gösterilir."}
