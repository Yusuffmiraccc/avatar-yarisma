from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import BigId, Money, Qty, UtcDateTime, created_at, fk, pk, ts, unit_fk, utcnow


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (CheckConstraint("initial_quantity >= 0", name="initial_qty_nonneg"),)
    id: Mapped[int] = pk()
    lot_code: Mapped[str] = mapped_column(String(80), unique=True)
    product_id: Mapped[int] = fk("products.id")
    supplier_id: Mapped[int | None] = fk("suppliers.id", nullable=True)
    received_at: Mapped[datetime | None] = ts()
    expiry_date: Mapped[date | None] = mapped_column(Date)
    initial_quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    # PURCHASE | PRODUCTION | BUTCHERING | REWORK | OPENING_STOCK
    lot_origin_type: Mapped[str] = mapped_column(String(24))
    # ACTIVE | EXHAUSTED | CLOSED  (blokaj ayrı tabloda)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")
    # Lot birim maliyeti: alış fiyatı veya EKP / parçalama tahsisi (SOZLESME §3.4)
    unit_cost: Mapped[Decimal | None] = mapped_column(Money)
    location_code: Mapped[str] = mapped_column(String(40), default="MAIN")
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        CheckConstraint("on_hand_quantity >= 0", name="on_hand_nonneg"),
        CheckConstraint("reserved_quantity >= 0", name="reserved_nonneg"),
    )
    lot_id: Mapped[int] = mapped_column(BigId, ForeignKey("lots.id"), primary_key=True)
    on_hand_quantity: Mapped[Decimal] = mapped_column(Qty, default=Decimal(0))
    reserved_quantity: Mapped[Decimal] = mapped_column(Qty, default=Decimal(0))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)


class StockMovement(Base):
    """Append-only defter. Güncelleme/silme yok; düzeltme ters hareketle yapılır."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("direction IN ('IN','OUT')", name="direction_valid"),
        Index("ix_stock_movements_lot_time", "lot_id", "occurred_at"),
        Index("ix_stock_movements_product_time", "product_id", "occurred_at"),
        Index("ix_stock_movements_source", "source_type", "source_id"),
        Index("ix_stock_movements_idem", "idempotency_key"),
    )
    id: Mapped[int] = pk()
    product_id: Mapped[int] = fk("products.id")
    lot_id: Mapped[int] = fk("lots.id")
    direction: Mapped[str] = mapped_column(String(3))
    movement_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int] = mapped_column(BigId)
    source_line_id: Mapped[int | None] = mapped_column(BigId)
    location_code: Mapped[str | None] = mapped_column(String(40))
    reverses_movement_id: Mapped[int | None] = fk("stock_movements.id", nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = ts(nullable=False)
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)


class LotBlock(Base):
    __tablename__ = "lot_blocks"
    __table_args__ = (Index("ix_lot_blocks_active", "lot_id", "unblocked_at"),)
    id: Mapped[int] = pk()
    lot_id: Mapped[int] = fk("lots.id")
    reason_code: Mapped[str] = mapped_column(String(40))
    reason_text: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int] = mapped_column(BigId)
    blocked_at: Mapped[datetime] = ts(nullable=False)
    blocked_by: Mapped[int | None] = fk("users.id", nullable=True)
    unblocked_at: Mapped[datetime | None] = ts()
    unblocked_by: Mapped[int | None] = fk("users.id", nullable=True)
    unblock_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()


class LotGenealogyEdge(Base):
    __tablename__ = "lot_genealogy_edges"
    __table_args__ = (
        CheckConstraint("source_lot_id <> target_lot_id", name="no_self_edge"),
        CheckConstraint("source_quantity >= 0 AND target_quantity >= 0", name="qty_nonneg"),
        Index("ix_genealogy_process", "process_type", "process_id"),
        UniqueConstraint("source_lot_id", "target_lot_id", "process_type", "process_id", name="uq_edge"),
    )
    id: Mapped[int] = pk()
    source_lot_id: Mapped[int] = fk("lots.id", index=True)
    target_lot_id: Mapped[int] = fk("lots.id", index=True)
    process_type: Mapped[str] = mapped_column(String(24))  # PRODUCTION | BUTCHERING | REWORK
    process_id: Mapped[int] = mapped_column(BigId)
    source_quantity: Mapped[Decimal] = mapped_column(Qty)
    source_unit_code: Mapped[str] = unit_fk()
    target_quantity: Mapped[Decimal] = mapped_column(Qty)
    target_unit_code: Mapped[str] = unit_fk()
    created_at: Mapped[datetime] = created_at()


class ReworkOrder(Base):
    """Yeniden işleme: bir lotun (kısmen) başka bir lota dönüşmesi; REWORK_ISSUE/REWORK_RECEIPT + genealogy."""

    __tablename__ = "rework_orders"
    __table_args__ = (CheckConstraint("input_quantity > 0 AND output_quantity > 0", name="qty_positive"),)
    id: Mapped[int] = pk()
    order_code: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED")
    input_lot_id: Mapped[int] = fk("lots.id")
    input_quantity: Mapped[Decimal] = mapped_column(Qty)
    output_lot_id: Mapped[int] = fk("lots.id")
    output_quantity: Mapped[Decimal] = mapped_column(Qty)
    unit_code: Mapped[str] = unit_fk()
    extra_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)
