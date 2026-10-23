from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Money, created_at, fk, pk, ts, unit_fk, updated_at


class Unit(Base):
    __tablename__ = "units"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    dimension: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = pk()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    # RAW_MATERIAL | INTERMEDIATE | FINISHED_GOOD | BYPRODUCT
    product_type: Mapped[str] = mapped_column(String(32))
    base_unit_code: Mapped[str] = unit_fk()
    requires_expiry_date: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime | None] = updated_at()


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = pk()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    # RAW_MATERIAL | OUTSOURCED_PROCESSOR | BOTH
    supplier_type: Mapped[str] = mapped_column(String(32))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime | None] = updated_at()


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = pk()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    # MARKET | BUSINESS | OTHER
    customer_type: Mapped[str] = mapped_column(String(32))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime | None] = updated_at()


class ProductPrice(Base):
    __tablename__ = "product_prices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_nonneg"),
        Index("ix_product_prices_lookup", "product_id", "price_type", "valid_from"),
    )
    id: Mapped[int] = pk()
    product_id: Mapped[int] = fk("products.id")
    price_type: Mapped[str] = mapped_column(String(24))  # PURCHASE | SALE | SERVICE
    amount: Mapped[Decimal] = mapped_column(Money)
    currency_code: Mapped[str] = mapped_column(String(3), default="EUR")
    unit_code: Mapped[str] = unit_fk()
    valid_from: Mapped[datetime] = ts(nullable=False)
    valid_to: Mapped[datetime | None] = ts()
    created_at: Mapped[datetime] = created_at()
    created_by: Mapped[int | None] = fk("users.id", nullable=True)
