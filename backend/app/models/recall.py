from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Qty, created_at, fk, pk, ts, unit_fk, updated_at


class Recall(Base):
    __tablename__ = "recalls"
    id: Mapped[int] = pk()
    recall_code: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT|ACTIVE|RESOLVED|CANCELLED
    reason_code: Mapped[str] = mapped_column(String(40))
    reason_text: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime | None] = ts()
    closed_at: Mapped[datetime | None] = ts()
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)
    updated_at: Mapped[datetime | None] = updated_at()


class RecallLot(Base):
    __tablename__ = "recall_lots"
    __table_args__ = (UniqueConstraint("recall_id", "lot_id"),)
    id: Mapped[int] = pk()
    recall_id: Mapped[int] = fk("recalls.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    role: Mapped[str] = mapped_column(String(24))  # ORIGIN | AFFECTED | DERIVED
    blocked_at: Mapped[datetime | None] = ts()
    created_at: Mapped[datetime] = created_at()


class RecallCustomerImpact(Base):
    __tablename__ = "recall_customer_impacts"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)
    id: Mapped[int] = pk()
    recall_id: Mapped[int] = fk("recalls.id", index=True)
    customer_id: Mapped[int] = fk("customers.id")
    lot_id: Mapped[int] = fk("lots.id")
    shipment_id: Mapped[int | None] = fk("shipments.id", nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    # PENDING | CONTACTED | ACKNOWLEDGED | UNREACHABLE | NOT_REQUIRED
    contact_status: Mapped[str] = mapped_column(String(24), default="PENDING")
    contacted_at: Mapped[datetime | None] = ts()
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = created_at()
