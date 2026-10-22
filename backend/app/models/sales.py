from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Money, Qty, created_at, fk, pk, ts, unit_fk


class Sale(Base):
    """Ticari kayıt. Fiziksel stok OUT'u dispatch yapar; satış stok düşürmez."""

    __tablename__ = "sales"
    __table_args__ = (CheckConstraint("total_amount >= 0", name="total_nonneg"),)
    id: Mapped[int] = pk()
    sale_code: Mapped[str] = mapped_column(String(80), unique=True)
    customer_id: Mapped[int | None] = fk("customers.id", nullable=True)
    shipment_id: Mapped[int | None] = fk("shipments.id", nullable=True)  # satış → dispatch bağı (SOZLESME §2)
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED")  # COMPLETED|VOIDED|REFUNDED
    sold_at: Mapped[datetime] = ts(nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    total_amount: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class SaleLine(Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        UniqueConstraint("sale_id", "line_number"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0 AND line_total >= 0", name="amount_nonneg"),
    )
    id: Mapped[int] = pk()
    sale_id: Mapped[int] = fk("sales.id")
    line_number: Mapped[int] = mapped_column()
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    unit_price: Mapped[Decimal] = mapped_column(Money)
    stock_movement_id: Mapped[int | None] = fk("stock_movements.id", nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Money)
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    created_at: Mapped[datetime] = created_at()


class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = pk()
    shipment_code: Mapped[str] = mapped_column(String(80), unique=True)
    customer_id: Mapped[int] = fk("customers.id")
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT|SHIPPED|CANCELLED|RETURNED
    shipped_at: Mapped[datetime | None] = ts()
    returned_at: Mapped[datetime | None] = ts()
    return_reason: Mapped[str | None] = mapped_column(String(500))
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class ShipmentLine(Base):
    __tablename__ = "shipment_lines"
    __table_args__ = (
        UniqueConstraint("shipment_id", "line_number"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )
    id: Mapped[int] = pk()
    shipment_id: Mapped[int] = fk("shipments.id")
    line_number: Mapped[int] = mapped_column()
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    stock_movement_id: Mapped[int | None] = fk("stock_movements.id", nullable=True)
    created_at: Mapped[datetime] = created_at()


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope_key", "idempotency_key"),)
    id: Mapped[int] = pk()
    scope_key: Mapped[str] = mapped_column(String(160))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(SmallInteger)
    response_body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at()
    expires_at: Mapped[datetime | None] = ts()
