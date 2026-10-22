from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import conflict, request_id_of
from app.models import ProductionOrder, Supplier
from app.schemas.common import Page, PageParams, paginate
from app.schemas.production import (CompleteIn, ProductionInputIn, ProductionOrderIn, ProductionOrderOut,
                                    ServiceCostIn)
from app.services import audit, production as svc

router = APIRouter(prefix="/production-orders", tags=["production"])
PP = Annotated[PageParams, Depends()]


@router.post("", response_model=ProductionOrderOut, status_code=201)
def create(body: ProductionOrderIn, db: DB, user=require("production:manage")):
    if db.scalar(select(ProductionOrder.id).where(ProductionOrder.order_code == body.order_code)):
        raise conflict("CONFLICT", "Üretim emri kodu zaten kayıtlı.", {"order_code": body.order_code})
    order = ProductionOrder(**body.model_dump(), status="DRAFT", created_by=user.id)
    db.add(order)
    db.flush()
    audit.record(db, actor_id=user.id, action="PRODUCTION_CREATED", entity_type="production_order", entity_id=order.id)
    return svc.to_out(db, order)


@router.get("", response_model=Page[ProductionOrderOut])
def list_orders(db: DB, p: PP, status: str | None = None, _=require("production:read")):
    stmt = select(ProductionOrder).order_by(ProductionOrder.id.desc())
    if status:
        stmt = stmt.where(ProductionOrder.status == status)
    res = paginate(db, stmt, p)
    res["items"] = [svc.to_out(db, o) for o in res["items"]]
    return res


@router.get("/{order_id}", response_model=ProductionOrderOut)
def get(order_id: int, db: DB, _=require("production:read")):
    return svc.to_out(db, svc.get_order(db, order_id))


@router.post("/{order_id}/inputs", response_model=ProductionOrderOut, status_code=201)
def add_input(order_id: int, body: ProductionInputIn, db: DB, _=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_input(db, order, body)
    return svc.to_out(db, order)


@router.post("/{order_id}/service-costs", response_model=ProductionOrderOut, status_code=201)
def add_service_cost(order_id: int, body: ServiceCostIn, db: DB, _=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_service_cost(db, order, body)
    return svc.to_out(db, order)


@router.post("/{order_id}/start", response_model=ProductionOrderOut)
def start(order_id: int, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.start(db, order, user.id)
    return svc.to_out(db, order)


@router.post("/{order_id}/complete", response_model=ProductionOrderOut)
def complete(order_id: int, body: CompleteIn, request: Request, db: DB, user=require("production:manage")):
    return svc.to_out(db, svc.complete(db, order_id, body, user.id, request_id_of(request)))


@router.post("/{order_id}/cancel", response_model=ProductionOrderOut)
def cancel(order_id: int, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.cancel(db, order, user.id)
    return svc.to_out(db, order)
