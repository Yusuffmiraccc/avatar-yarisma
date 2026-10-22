from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import not_found, request_id_of
from app.models import Sale, Shipment
from app.schemas.common import Page, PageParams, paginate
from app.schemas.sales import SaleIn, SaleOut, ShipmentIn, ShipmentOut
from app.services import idempotency, sales as svc

router = APIRouter(tags=["sales"])
PP = Annotated[PageParams, Depends()]
IdemKey = Annotated[str | None, Header(alias="Idempotency-Key")]


class VoidIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/sales", response_model=SaleOut, status_code=201)
def create_sale(body: SaleIn, request: Request, db: DB, idempotency_key: IdemKey = None, user=require("sales:create")):
    def action():
        sale = svc.create_sale(db, body, user.id, request_id_of(request))
        return 201, svc.sale_out(db, sale)

    return idempotency.run(db, scope=f"POST:/sales:{user.id}", key=idempotency_key, body=body, required=True,
                           action=action)


@router.get("/sales", response_model=Page[SaleOut])
def list_sales(db: DB, p: PP, status: str | None = None, customer_id: int | None = None, _=require("sales:read")):
    stmt = select(Sale).order_by(Sale.id.desc())
    if status:
        stmt = stmt.where(Sale.status == status)
    if customer_id:
        stmt = stmt.where(Sale.customer_id == customer_id)
    res = paginate(db, stmt, p)
    res["items"] = [svc.sale_out(db, s) for s in res["items"]]
    return res


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: DB, _=require("sales:read")):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise not_found("Satış", sale_id)
    return svc.sale_out(db, sale)


@router.post("/sales/{sale_id}/void", response_model=SaleOut)
def void_sale(sale_id: int, body: VoidIn, request: Request, db: DB, user=require("sales:void")):
    return svc.sale_out(db, svc.void_sale(db, sale_id, body.reason, user.id, request_id_of(request)))


@router.post("/shipments", response_model=ShipmentOut, status_code=201)
def create_shipment(body: ShipmentIn, db: DB, user=require("shipments:manage")):
    return svc.shipment_out(db, svc.create_shipment(db, body, user.id))


@router.get("/shipments", response_model=Page[ShipmentOut])
def list_shipments(db: DB, p: PP, status: str | None = None, customer_id: int | None = None, _=require("shipments:read")):
    stmt = select(Shipment).order_by(Shipment.id.desc())
    if status:
        stmt = stmt.where(Shipment.status == status)
    if customer_id:
        stmt = stmt.where(Shipment.customer_id == customer_id)
    res = paginate(db, stmt, p)
    res["items"] = [svc.shipment_out(db, s) for s in res["items"]]
    return res


@router.get("/shipments/{shipment_id}", response_model=ShipmentOut)
def get_shipment(shipment_id: int, db: DB, _=require("shipments:read")):
    return svc.shipment_out(db, svc.get_shipment(db, shipment_id))


@router.post("/shipments/{shipment_id}/dispatch", response_model=ShipmentOut)
def dispatch(shipment_id: int, request: Request, db: DB, idempotency_key: IdemKey = None, user=require("shipments:manage")):
    def action():
        sh = svc.get_shipment(db, shipment_id)
        return 200, svc.shipment_out(db, svc.dispatch(db, sh, user.id, request_id_of(request)))

    return idempotency.run(db, scope=f"POST:/shipments/{shipment_id}/dispatch:{user.id}", key=idempotency_key,
                           body={"shipment_id": shipment_id}, required=True, action=action)


@router.post("/shipments/{shipment_id}/cancel", response_model=ShipmentOut)
def cancel_shipment(shipment_id: int, db: DB, user=require("shipments:manage")):
    sh = svc.get_shipment(db, shipment_id, lock=True)
    svc.cancel_shipment(db, sh, user.id)
    return svc.shipment_out(db, sh)
