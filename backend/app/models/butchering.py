from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Money, Qty, created_at, fk, pk, ts, unit_fk


class ButcheringOrder(Base):
    __tablename__ = "butchering_orders"
    __table_args__ = (
        CheckConstraint("input_weight > 0", name="input_weight_positive"),
        CheckConstraint("total_purchase_cost >= 0", name="cost_nonneg"),
    )
    id: Mapped[int] = pk()
    order_code: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    animal_type: Mapped[str] = mapped_column(String(40))
    input_weight: Mapped[Decimal] = mapped_column(Qty)
    input_unit_code: Mapped[str] = unit_fk()
    total_purchase_cost: Mapped[Decimal] = mapped_column(Money)
    declared_unit_price: Mapped[Decimal | None] = mapped_column(Money)  # kaynak belgedeki birim fiyat (tutarsızlık kontrolü)
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    allocation_method: Mapped[str] = mapped_column(String(24), default="BY_WEIGHT")  # BY_WEIGHT | BY_VALUE
    weight_difference: Mapped[Decimal | None] = mapped_column(Qty)
    started_at: Mapped[datetime | None] = ts()
    completed_at: Mapped[datetime | None] = ts()
    notes: Mapped[str | None] = mapped_column(String(1000))
    is_demo: Mapped[bool] = mapped_column(default=False)
    reversed_at: Mapped[datetime | None] = ts()
    reversed_by: Mapped[int | None] = fk("users.id", nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class ButcheringInput(Base):
    __tablename__ = "butchering_inputs"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)
    id: Mapped[int] = pk()
    butchering_order_id: Mapped[int] = fk("butchering_orders.id", index=True)
    lot_id: Mapped[int] = fk("lots.id", index=True)
    product_id: Mapped[int] = fk("products.id")
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    cost_snapshot: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at()


class ButcheringOutput(Base):
    __tablename__ = "butchering_outputs"
    __table_args__ = (
        CheckConstraint("actual_weight >= 0", name="weight_nonneg"),
        CheckConstraint("allocated_cost >= 0", name="cost_nonneg"),
    )
    id: Mapped[int] = pk()
    butchering_order_id: Mapped[int] = fk("butchering_orders.id", index=True)
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id", index=True)
    output_type: Mapped[str] = mapped_column(String(24))  # CUT | BYPRODUCT
    actual_weight: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    expected_weight: Mapped[Decimal | None] = mapped_column(Qty)  # reçeteden
    allocation_weight: Mapped[Decimal | None] = mapped_column(Qty)
    allocation_value: Mapped[Decimal | None] = mapped_column(Money)
    allocated_cost: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at()


class ButcheringWasteRecord(Base):
    __tablename__ = "butchering_waste_records"
    __table_args__ = (
        CheckConstraint("actual_weight >= 0", name="weight_nonneg"),
        CheckConstraint("allocated_cost >= 0", name="cost_nonneg"),
    )
    id: Mapped[int] = pk()
    butchering_order_id: Mapped[int] = fk("butchering_orders.id", index=True)
    input_lot_id: Mapped[int] = fk("lots.id")
    actual_weight: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    # TRIMMING_LOSS | BONE_WASTE | CONTAMINATION | SPOILAGE | PROCESS_LOSS | OTHER
    reason_code: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(String(1000))
    allocated_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    created_at: Mapped[datetime] = created_at()


class ButcheringRecipeLine(Base):
    """Önceden tanımlı parçalama reçetesi / dağıtım anahtarı (PDF Görev 2)."""

    __tablename__ = "butchering_recipe_lines"
    __table_args__ = (CheckConstraint("expected_ratio >= 0 AND expected_ratio <= 1", name="ratio_range"),)
    id: Mapped[int] = pk()
    animal_type: Mapped[str] = mapped_column(String(40), index=True)
    product_id: Mapped[int] = fk("products.id")
    output_type: Mapped[str] = mapped_column(String(24))  # CUT | BYPRODUCT | WASTE
    expected_ratio: Mapped[Decimal] = mapped_column(Qty)  # girdi ağırlığına oran
    created_at: Mapped[datetime] = created_at()


class WeightVarianceRecord(Base):
    """Ağırlık dengesi toleransı aşımı: gerekçe + yetkili onay (SOZLESME §3.2)."""

    __tablename__ = "weight_variance_records"
    id: Mapped[int] = pk()
    butchering_order_id: Mapped[int] = fk("butchering_orders.id", index=True)
    variance_weight: Mapped[Decimal] = mapped_column(Qty)
    tolerance_weight: Mapped[Decimal] = mapped_column(Qty)
    reason_text: Mapped[str] = mapped_column(String(500))
    allocated_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))  # açıklanan fark için maliyet payı
    approved_by: Mapped[int] = fk("users.id")
    created_at: Mapped[datetime] = created_at()
