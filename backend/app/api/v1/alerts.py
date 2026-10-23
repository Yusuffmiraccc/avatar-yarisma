from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import not_found
from app.models import AnomalyAlert
from app.models.types import utcnow
from app.schemas.common import ApiModel, Page, PageParams, paginate, redact_cost_data

router = APIRouter(prefix="/alerts", tags=["alerts"])
PP = Annotated[PageParams, Depends()]


def _alert_response(value, user):
    content = jsonable_encoder(value)
    if "costs:read" not in user.permissions:
        content = redact_cost_data(content)
    return JSONResponse(content=content)


class AlertOut(ApiModel):
    id: int
    alert_type: str
    severity: str
    entity_type: str
    entity_id: int
    message: str
    details: dict | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime


@router.get("", response_model=Page[AlertOut])
def list_alerts(db: DB, p: PP, alert_type: str | None = None, open_only: bool = False,
                user=require("alerts:read")):
    stmt = select(AnomalyAlert).order_by(AnomalyAlert.id.desc())
    if alert_type:
        stmt = stmt.where(AnomalyAlert.alert_type == alert_type)
    if open_only:
        stmt = stmt.where(AnomalyAlert.acknowledged_at.is_(None))
    return _alert_response(paginate(db, stmt, p), user)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge(alert_id: int, db: DB, user=require("alerts:manage")):
    a = db.get(AnomalyAlert, alert_id)
    if a is None:
        raise not_found("Uyarı", alert_id)
    a.acknowledged_at = utcnow()
    return _alert_response(a, user)


@router.post("/scan", response_model=list[AlertOut])
def scan(db: DB, user=require("alerts:manage")):
    """Kural/istatistik taraması çalıştırır; yeni üretilen uyarıları döner (idempotent)."""
    from app.services import anomaly
    return _alert_response(anomaly.scan(db), user)
