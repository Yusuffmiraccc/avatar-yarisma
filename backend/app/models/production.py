from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Money, Qty, created_at, fk, pk, ts, unit_fk, updated_at


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    id: Mapped[int] = pk()
    order_code: Mapped[str] = mapped_column(String(80), unique=True)
    production_type: Mapped[str] = mapped_column(String(32))  # IN_HOUSE | OUTSOURCED
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT|IN_PROGRESS|COMPLETED|CANCELLED
    planned_quantity: Mapped[Decimal | None] = mapped_column(Qty)
    planned_unit_code: Mapped[str | None] = unit_fk(nullable=True)
    started_at: Mapped[datetime | None] = ts()
    completed_at: Mapped[datetime | None] = ts()
    supplier_id: Mapped[int | None] = fk("suppliers.id", nullable=True)
    # Tamamlamada hesaplanan snapshot'lar (SOZLESME §3.4)
    total_input_cost: Mapped[Decimal | None] = mapped_column(Money)
    total_service_cost: Mapped[Decimal | None] = mapped_column(Money)
    total_cost: Mapped[Decimal | None] = mapped_column(Money)
    actual_output_quantity: Mapped[Decimal | None] = mapped_column(Qty)
    unit_cost_ekp: Mapped[Decimal | None] = mapped_column(Money)
    notes: Mapped[str | None] = mapped_column(String(1000))
    is_demo: Mapped[bool] = mapped_column(default=False)
    reversed_at: Mapped[datetime | None] = ts()
    reversed_by: Mapped[int | None] = fk("users.id", nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)
    updated_at: Mapped[datetime | None] = updated_at()


class ProductionInput(Base):
    __tablename__ = "production_inputs"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_cost >= 0 AND total_cost >= 0", name="cost_nonneg"),
    )
    id: Mapped[int] = pk()
    production_order_id: Mapped[int] = fk("production_orders.id", index=True)
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    unit_cost: Mapped[Decimal] = mapped_column(Money)
    total_cost: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at()


class ProductionOutput(Base):
    __tablename__ = "production_outputs"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)
    id: Mapped[int] = pk()
    production_order_id: Mapped[int] = fk("production_orders.id", index=True)
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    unit_cost: Mapped[Decimal | None] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at()


class ProductionServiceCost(Base):
    __tablename__ = "production_service_costs"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_nonneg"),)
    id: Mapped[int] = pk()
    production_order_id: Mapped[int] = fk("production_orders.id", index=True)
    supplier_id: Mapped[int | None] = fk("suppliers.id", nullable=True)
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal | None] = mapped_column(Qty)
    unit_price: Mapped[Decimal | None] = mapped_column(Money)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    occurred_at: Mapped[datetime] = ts(nullable=False)
    created_at: Mapped[datetime] = created_at()
