from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import request_id_of
from app.models import Lot, ReworkOrder
from app.schemas.butchering import ButcheringOrderOut
from app.schemas.common import ApiModel, Dec, Page, PageParams, paginate, redact_cost_data
from app.schemas.production import ProductionOrderOut
from app.schemas.sales import ShipmentOut
from app.services import butchering as but_svc
from app.services import corrections as svc
from app.services import production as prod_svc
from app.services import sales as sales_svc

router = APIRouter(tags=["corrections"])
PP = Annotated[PageParams, Depends()]


class ReasonIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class ReworkIn(BaseModel):
    order_code: str = Field(min_length=1, max_length=80)
    input_lot_id: int
    input_quantity: Dec
    output_product_id: int
    output_lot_code: str = Field(min_length=1, max_length=80)
    output_quantity: Dec
    extra_cost: Dec = 0
    reason: str = Field(min_length=3, max_length=500)


class ReworkOut(ApiModel):
    id: int
    order_code: str
    status: str
    input_lot_id: int
    input_lot_code: str | None = None
    input_quantity: Dec
    output_lot_id: int
    output_lot_code: str | None = None
    output_quantity: Dec
    unit_code: str
    extra_cost: Dec
    reason: str
    created_at: datetime


def rework_out(db, r: ReworkOrder) -> ReworkOut:
    codes = {l.id: l.lot_code for l in db.scalars(select(Lot).where(Lot.id.in_([r.input_lot_id, r.output_lot_id])))}
    return ReworkOut.model_validate(r).model_copy(update={"input_lot_code": codes.get(r.input_lot_id),
                                                          "output_lot_code": codes.get(r.output_lot_id)})


@router.post("/production-orders/{order_id}/reverse", response_model=ProductionOrderOut)
def reverse_production(order_id: int, body: ReasonIn, request: Request, db: DB, user=require("corrections:manage")):
    return prod_svc.to_out(db, svc.reverse_production(db, order_id, body.reason, user.id, request_id_of(request)))


@router.post("/butchering-orders/{order_id}/reverse", response_model=ButcheringOrderOut)
def reverse_butchering(order_id: int, body: ReasonIn, request: Request, db: DB, user=require("corrections:manage")):
    return but_svc.to_out(db, svc.reverse_butchering(db, order_id, body.reason, user.id, request_id_of(request)))


@router.post("/shipments/{shipment_id}/return", response_model=ShipmentOut)
def return_shipment(shipment_id: int, body: ReasonIn, request: Request, db: DB, user=require("shipments:manage")):
    return sales_svc.shipment_out(db, svc.return_shipment(db, shipment_id, body.reason, user.id, request_id_of(request)))


@router.post("/rework-orders", response_model=ReworkOut, status_code=201)
def create_rework(body: ReworkIn, request: Request, db: DB, user=require("production:manage")):
    ro = svc.rework(db, order_code=body.order_code, input_lot_id=body.input_lot_id, input_quantity=body.input_quantity,
                    output_product_id=body.output_product_id, output_lot_code=body.output_lot_code,
                    output_quantity=body.output_quantity, extra_cost=body.extra_cost, reason=body.reason,
                    user_id=user.id, request_id=request_id_of(request))
    out = rework_out(db, ro)
    content = jsonable_encoder(out) if "costs:read" in user.permissions else redact_cost_data(out)
    return JSONResponse(status_code=201, content=content)


@router.get("/rework-orders", response_model=Page[ReworkOut])
def list_rework(db: DB, p: PP, user=require("production:read")):
    res = paginate(db, select(ReworkOrder).order_by(ReworkOrder.id.desc()), p)
    res["items"] = [rework_out(db, r) for r in res["items"]]
    content = jsonable_encoder(res) if "costs:read" in user.permissions else redact_cost_data(res)
    return JSONResponse(content=content)
