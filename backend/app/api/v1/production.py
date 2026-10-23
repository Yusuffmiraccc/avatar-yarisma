from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import conflict, request_id_of
from app.models import ProductionOrder
from app.schemas.common import Page, PageParams, paginate, redact_cost_data
from app.schemas.production import (
    CompleteIn,
    ProductionInputIn,
    ProductionOrderIn,
    ProductionOrderOut,
    ServiceCostIn,
)
from app.services import audit
from app.services import production as svc

router = APIRouter(prefix="/production-orders", tags=["production"])
PP = Annotated[PageParams, Depends()]


def _order_response(db, order, user, status_code: int = 200):
    data = svc.to_out(db, order)
    content = jsonable_encoder(data) if "costs:read" in user.permissions else redact_cost_data(data)
    return JSONResponse(status_code=status_code, content=content)


@router.post("", response_model=ProductionOrderOut, status_code=201)
def create(body: ProductionOrderIn, db: DB, user=require("production:manage")):
    if db.scalar(select(ProductionOrder.id).where(ProductionOrder.order_code == body.order_code)):
        raise conflict("CONFLICT", "Üretim emri kodu zaten kayıtlı.", {"order_code": body.order_code})
    order = ProductionOrder(**body.model_dump(), status="DRAFT", created_by=user.id)
    db.add(order)
    db.flush()
    audit.record(db, actor_id=user.id, action="PRODUCTION_CREATED", entity_type="production_order", entity_id=order.id)
    return _order_response(db, order, user, 201)


@router.get("", response_model=Page[ProductionOrderOut])
def list_orders(db: DB, p: PP, status: str | None = None, user=require("production:read")):
    stmt = select(ProductionOrder).order_by(ProductionOrder.id.desc())
    if status:
        stmt = stmt.where(ProductionOrder.status == status)
    res = paginate(db, stmt, p)
    res["items"] = svc.to_out_many(db, res["items"])
    content = jsonable_encoder(res) if "costs:read" in user.permissions else redact_cost_data(res)
    return JSONResponse(content=content)


@router.get("/{order_id}", response_model=ProductionOrderOut)
def get(order_id: int, db: DB, user=require("production:read")):
    return _order_response(db, svc.get_order(db, order_id), user)


@router.post("/{order_id}/inputs", response_model=ProductionOrderOut, status_code=201)
def add_input(order_id: int, body: ProductionInputIn, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_input(db, order, body)
    return _order_response(db, order, user, 201)


@router.post("/{order_id}/service-costs", response_model=ProductionOrderOut, status_code=201)
def add_service_cost(order_id: int, body: ServiceCostIn, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_service_cost(db, order, body)
    return _order_response(db, order, user, 201)


@router.post("/{order_id}/start", response_model=ProductionOrderOut)
def start(order_id: int, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.start(db, order, user.id)
    return _order_response(db, order, user)


@router.post("/{order_id}/complete", response_model=ProductionOrderOut)
def complete(order_id: int, body: CompleteIn, request: Request, db: DB, user=require("production:manage")):
    return _order_response(db, svc.complete(db, order_id, body, user.id, request_id_of(request)), user)


@router.post("/{order_id}/cancel", response_model=ProductionOrderOut)
def cancel(order_id: int, db: DB, user=require("production:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.cancel(db, order, user.id)
    return _order_response(db, order, user)
