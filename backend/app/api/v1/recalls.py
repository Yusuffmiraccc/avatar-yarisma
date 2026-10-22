from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import not_found, request_id_of
from app.models import Customer, Lot, Recall, RecallCustomerImpact, RecallLot
from app.schemas.catalog import LotOut
from app.schemas.common import ApiModel, Dec, Page, PageParams, paginate
from app.services import recall as svc
from app.services import traceability
from app.api.v1.catalog import lot_out

router = APIRouter(tags=["traceability"])
PP = Annotated[PageParams, Depends()]


class RecallIn(BaseModel):
    recall_code: str = Field(min_length=1, max_length=80)
    reason_code: str = Field(min_length=1, max_length=40)
    reason_text: str | None = Field(default=None, max_length=1000)
    lot_codes: list[str] = Field(min_length=1)


class ImpactOut(ApiModel):
    id: int
    customer_id: int
    customer_code: str | None = None
    customer_name: str | None = None
    phone: str | None = None
    email: str | None = None
    lot_id: int
    lot_code: str | None = None
    shipment_id: int | None = None
    quantity: Dec
    unit_code: str
    contact_status: str
    contacted_at: datetime | None = None
    notes: str | None = None


class RecallLotOut(ApiModel):
    lot_id: int
    lot_code: str
    role: str
    blocked_at: datetime | None = None


class RecallOut(ApiModel):
    id: int
    recall_code: str
    status: str
    reason_code: str
    reason_text: str | None = None
    started_at: datetime | None = None
    closed_at: datetime | None = None
    lots: list[RecallLotOut] = []
    impacts: list[ImpactOut] = []
    total_shipped_quantity: Dec | None = None
    second_tier_note: str = traceability.SECOND_TIER_NOTE


class ImpactPatch(BaseModel):
    contact_status: Literal["PENDING", "CONTACTED", "ACKNOWLEDGED", "UNREACHABLE", "NOT_REQUIRED"]
    notes: str | None = Field(default=None, max_length=1000)


class UnblockIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


def recall_out(db, r: Recall) -> RecallOut:
    lots = db.execute(select(RecallLot, Lot).join(Lot, Lot.id == RecallLot.lot_id)
                      .where(RecallLot.recall_id == r.id).order_by(RecallLot.id)).all()
    imps = db.execute(select(RecallCustomerImpact, Customer, Lot)
                      .join(Customer, Customer.id == RecallCustomerImpact.customer_id)
                      .join(Lot, Lot.id == RecallCustomerImpact.lot_id)
                      .where(RecallCustomerImpact.recall_id == r.id).order_by(RecallCustomerImpact.id)).all()
    out = RecallOut.model_validate(r)
    out.lots = [RecallLotOut(lot_id=l.id, lot_code=l.lot_code, role=rl.role, blocked_at=rl.blocked_at) for rl, l in lots]
    out.impacts = [ImpactOut.model_validate(i).model_copy(update={
        "customer_code": c.code, "customer_name": c.name, "phone": c.phone, "email": c.email, "lot_code": l.lot_code})
        for i, c, l in imps]
    out.total_shipped_quantity = sum((i.quantity for i, _, _ in imps), 0) if imps else None
    return out


# ---- izleme -------------------------------------------------------------------------------------------------
@router.get("/traceability/lots/{lot_id}/forward", response_model=traceability.ForwardResult)
def forward(lot_id: int, db: DB, _=require("traceability:read")):
    return traceability.forward(db, [lot_id])


@router.get("/traceability/lots/by-code/{lot_code}/forward", response_model=traceability.ForwardResult)
def forward_by_code(lot_code: str, db: DB, _=require("traceability:read")):
    lot = db.scalar(select(Lot).where(Lot.lot_code == lot_code))
    if lot is None:
        raise not_found("Lot", lot_code)
    return traceability.forward(db, [lot.id])


@router.get("/traceability/lots/{lot_id}/backward", response_model=traceability.BackwardResult)
def backward(lot_id: int, db: DB, _=require("traceability:read")):
    return traceability.backward(db, lot_id)


@router.get("/traceability/lots/by-code/{lot_code}/backward", response_model=traceability.BackwardResult)
def backward_by_code(lot_code: str, db: DB, _=require("traceability:read")):
    lot = db.scalar(select(Lot).where(Lot.lot_code == lot_code))
    if lot is None:
        raise not_found("Lot", lot_code)
    return traceability.backward(db, lot.id)


@router.get("/traceability/lots/{lot_id}/graph")
def graph(lot_id: int, db: DB, _=require("traceability:read")):
    return traceability.graph(db, lot_id)


# ---- geri çağırma ---------------------------------------------------------------------------------------------
@router.post("/recalls", response_model=RecallOut, status_code=201)
def create_recall(body: RecallIn, db: DB, user=require("recalls:manage")):
    r = svc.create(db, recall_code=body.recall_code, reason_code=body.reason_code, reason_text=body.reason_text,
                   lot_codes=body.lot_codes, user_id=user.id)
    return recall_out(db, r)


@router.get("/recalls", response_model=Page[RecallOut])
def list_recalls(db: DB, p: PP, status: str | None = None, _=require("recalls:read")):
    stmt = select(Recall).order_by(Recall.id.desc())
    if status:
        stmt = stmt.where(Recall.status == status)
    res = paginate(db, stmt, p)
    res["items"] = [recall_out(db, r) for r in res["items"]]
    return res


@router.get("/recalls/{recall_id}", response_model=RecallOut)
def get_recall(recall_id: int, db: DB, _=require("recalls:read")):
    return recall_out(db, svc.get_recall(db, recall_id))


@router.get("/recalls/{recall_id}/simulation", response_model=traceability.ForwardResult)
def simulate(recall_id: int, db: DB, _=require("recalls:read")):
    return svc.simulate(db, svc.get_recall(db, recall_id))


@router.post("/recalls/{recall_id}/activate", response_model=RecallOut)
def activate(recall_id: int, request: Request, db: DB, user=require("recalls:manage")):
    return recall_out(db, svc.activate(db, recall_id, user.id, request_id_of(request)))


@router.post("/recalls/{recall_id}/resolve", response_model=RecallOut)
def resolve(recall_id: int, request: Request, db: DB, user=require("recalls:resolve")):
    return recall_out(db, svc.resolve(db, recall_id, user.id, request_id_of(request)))


@router.post("/recalls/{recall_id}/cancel", response_model=RecallOut)
def cancel(recall_id: int, db: DB, user=require("recalls:manage")):
    return recall_out(db, svc.cancel(db, recall_id, user.id))


@router.patch("/recalls/{recall_id}/impacts/{impact_id}", response_model=ImpactOut)
def patch_impact(recall_id: int, impact_id: int, body: ImpactPatch, db: DB, _=require("recalls:manage")):
    from app.models.types import utcnow
    imp = db.get(RecallCustomerImpact, impact_id)
    if imp is None or imp.recall_id != recall_id:
        raise not_found("Etkilenen müşteri kaydı", impact_id)
    imp.contact_status, imp.notes = body.contact_status, body.notes
    if body.contact_status in ("CONTACTED", "ACKNOWLEDGED"):
        imp.contacted_at = utcnow()
    db.flush()
    c, l = db.get(Customer, imp.customer_id), db.get(Lot, imp.lot_id)
    return ImpactOut.model_validate(imp).model_copy(update={"customer_code": c.code, "customer_name": c.name,
                                                            "phone": c.phone, "email": c.email, "lot_code": l.lot_code})


@router.post("/lots/{lot_id}/unblock", response_model=LotOut)
def unblock(lot_id: int, body: UnblockIn, request: Request, db: DB, user=require("lots:unblock")):
    lot = svc.unblock_lot(db, lot_id, body.reason, user.id, request_id_of(request))
    return lot_out(db, lot)
