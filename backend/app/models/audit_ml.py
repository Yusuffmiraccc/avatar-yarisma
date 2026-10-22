from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import BigId, Money, Qty, created_at, fk, pk, ts


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = pk()
    actor_user_id: Mapped[int | None] = fk("users.id", nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int] = mapped_column(BigId)
    occurred_at: Mapped[datetime] = ts(nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict | None] = mapped_column(JSON)


class MlPrediction(Base):
    __tablename__ = "ml_predictions"
    id: Mapped[int] = pk()
    prediction_type: Mapped[str] = mapped_column(String(40))  # PRODUCTION_YIELD_EKP | BUTCHERING_OUTPUT_WEIGHT
    model_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16), default="SUCCEEDED")  # SUCCEEDED | FAILED
    input_reference_type: Mapped[str | None] = mapped_column(String(40))
    input_reference_id: Mapped[int | None] = mapped_column(BigId)
    input_summary: Mapped[dict | None] = mapped_column(JSON)
    predicted_value: Mapped[Decimal | None] = mapped_column(Qty)
    predicted_cost: Mapped[Decimal | None] = mapped_column(Money)
    baseline_value: Mapped[Decimal | None] = mapped_column(Qty)
    baseline_cost: Mapped[Decimal | None] = mapped_column(Money)
    actual_value: Mapped[Decimal | None] = mapped_column(Qty)
    actual_cost: Mapped[Decimal | None] = mapped_column(Money)
    metric_name: Mapped[str | None] = mapped_column(String(40))
    error_value: Mapped[Decimal | None] = mapped_column(Qty)
    detail: Mapped[dict | None] = mapped_column(JSON)  # parça bazlı tahminler vb.
    limitations_note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class AnomalyAlert(Base):
    """Kural/istatistik tabanlı uyarı (fire, maliyet artışı, düşük verim, lot tutarsızlığı)."""

    __tablename__ = "anomaly_alerts"
    id: Mapped[int] = pk()
    alert_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(12))  # INFO | WARNING | CRITICAL
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(BigId)
    message: Mapped[str] = mapped_column(String(500))
    details: Mapped[dict | None] = mapped_column(JSON)
    acknowledged_at: Mapped[datetime | None] = ts()
    created_at: Mapped[datetime] = created_at()


class DocumentExtraction(Base):
    """Fatura/irsaliye okuma ÖNERİSİ. İnsan onayı olmadan hiçbir stok/maliyet kaydı oluşmaz."""

    __tablename__ = "document_extractions"
    id: Mapped[int] = pk()
    doc_type: Mapped[str] = mapped_column(String(24))  # INVOICE | DELIVERY_NOTE
    source_name: Mapped[str | None] = mapped_column(String(200))
    raw_text: Mapped[str] = mapped_column(Text)
    proposed: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_REVIEW")  # PENDING_REVIEW|APPROVED|REJECTED
    reviewed_by: Mapped[int | None] = fk("users.id", nullable=True)
    reviewed_at: Mapped[datetime | None] = ts()
    review_note: Mapped[str | None] = mapped_column(String(500))
    resulting_lot_ids: Mapped[list | None] = mapped_column(JSON)
    created_by: Mapped[int | None] = fk("users.id", nullable=True)
    created_at: Mapped[datetime] = created_at()
