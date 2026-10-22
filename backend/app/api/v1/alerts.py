from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import not_found
from app.models import AnomalyAlert
from app.models.types import utcnow
from app.schemas.common import ApiModel, Page, PageParams, paginate
from datetime import datetime

router = APIRouter(prefix="/alerts", tags=["alerts"])
PP = Annotated[PageParams, Depends()]


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
def list_alerts(db: DB, p: PP, alert_type: str | None = None, open_only: bool = False, _=require("alerts:read")):
    stmt = select(AnomalyAlert).order_by(AnomalyAlert.id.desc())
    if alert_type:
        stmt = stmt.where(AnomalyAlert.alert_type == alert_type)
    if open_only:
        stmt = stmt.where(AnomalyAlert.acknowledged_at.is_(None))
    return paginate(db, stmt, p)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge(alert_id: int, db: DB, _=require("alerts:manage")):
    a = db.get(AnomalyAlert, alert_id)
    if a is None:
        raise not_found("Uyarı", alert_id)
    a.acknowledged_at = utcnow()
    return a


@router.post("/scan", response_model=list[AlertOut])
def scan(db: DB, _=require("alerts:manage")):
    """Kural/istatistik taraması çalıştırır; yeni üretilen uyarıları döner (idempotent)."""
    from app.services import anomaly
    return anomaly.scan(db)
