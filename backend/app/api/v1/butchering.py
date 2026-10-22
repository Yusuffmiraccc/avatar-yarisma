from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core.deps import DB, CurrentUserDep, require
from app.core.errors import request_id_of
from app.models import ButcheringOrder
from app.schemas.butchering import (ButcheringCompleteIn, ButcheringInputIn, ButcheringOrderIn, ButcheringOrderOut,
                                    RecipeIn, RecipeOut, WasteIn)
from app.schemas.common import Page, PageParams, paginate
from app.services import butchering as svc

router = APIRouter(tags=["butchering"])
PP = Annotated[PageParams, Depends()]


@router.put("/butchering-recipes/{animal_type}", response_model=RecipeOut)
def put_recipe(animal_type: str, body: RecipeIn, db: DB, _=require("butchering:manage")):
    return svc.set_recipe(db, animal_type, body)


@router.get("/butchering-recipes/{animal_type}", response_model=RecipeOut)
def get_recipe(animal_type: str, db: DB, _=require("butchering:read")):
    return svc.get_recipe(db, animal_type)


@router.post("/butchering-orders", response_model=ButcheringOrderOut, status_code=201)
def create(body: ButcheringOrderIn, db: DB, user=require("butchering:manage")):
    order = svc.create(db, ButcheringOrder(**body.model_dump()), user.id)
    return svc.to_out(db, order)


@router.get("/butchering-orders", response_model=Page[ButcheringOrderOut])
def list_orders(db: DB, p: PP, status: str | None = None, _=require("butchering:read")):
    stmt = select(ButcheringOrder).order_by(ButcheringOrder.id.desc())
    if status:
        stmt = stmt.where(ButcheringOrder.status == status)
    res = paginate(db, stmt, p)
    res["items"] = [svc.to_out(db, o) for o in res["items"]]
    return res


@router.get("/butchering-orders/{order_id}", response_model=ButcheringOrderOut)
def get(order_id: int, db: DB, _=require("butchering:read")):
    return svc.to_out(db, svc.get_order(db, order_id))


@router.post("/butchering-orders/{order_id}/inputs", response_model=ButcheringOrderOut, status_code=201)
def add_input(order_id: int, body: ButcheringInputIn, db: DB, _=require("butchering:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_input(db, order, body)
    return svc.to_out(db, order)


@router.post("/butchering-orders/{order_id}/waste-records", response_model=ButcheringOrderOut, status_code=201)
def add_waste(order_id: int, body: WasteIn, db: DB, _=require("butchering:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.add_waste(db, order, body)
    return svc.to_out(db, order)


@router.post("/butchering-orders/{order_id}/start", response_model=ButcheringOrderOut)
def start(order_id: int, db: DB, user=require("butchering:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.start(db, order, user.id)
    return svc.to_out(db, order)


@router.post("/butchering-orders/{order_id}/complete", response_model=ButcheringOrderOut)
def complete(order_id: int, body: ButcheringCompleteIn, request: Request, db: DB, user: CurrentUserDep,
             _=require("butchering:manage")):
    return svc.to_out(db, svc.complete(db, order_id, body, user, request_id_of(request)))


@router.post("/butchering-orders/{order_id}/cancel", response_model=ButcheringOrderOut)
def cancel(order_id: int, db: DB, user=require("butchering:manage")):
    order = svc.get_order(db, order_id, lock=True)
    svc.cancel(db, order, user.id)
    return svc.to_out(db, order)
