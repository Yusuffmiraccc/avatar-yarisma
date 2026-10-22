from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, Dec


class UnitOut(ApiModel):
    code: str
    name: str
    dimension: str


ProductType = Literal["RAW_MATERIAL", "INTERMEDIATE", "FINISHED_GOOD", "BYPRODUCT"]


class ProductIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    product_type: ProductType
    base_unit_code: str
    is_lot_tracked: bool = True
    requires_expiry_date: bool = False


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None
    requires_expiry_date: bool | None = None


class ProductOut(ApiModel):
    id: int
    code: str
    name: str
    product_type: str
    base_unit_code: str
    is_lot_tracked: bool
    requires_expiry_date: bool
    is_active: bool
    updated_at: datetime | None = None


class PartyIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    type: str
    phone: str | None = None
    email: str | None = None


class PartyPatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None


class SupplierOut(ApiModel):
    id: int
    code: str
    name: str
    supplier_type: str
    phone: str | None = None
    email: str | None = None
    is_active: bool
    updated_at: datetime | None = None


class CustomerOut(ApiModel):
    id: int
    code: str
    name: str
    customer_type: str
    phone: str | None = None
    email: str | None = None
    is_active: bool
    updated_at: datetime | None = None


class PriceIn(BaseModel):
    price_type: Literal["PURCHASE", "SALE", "SERVICE"]
    amount: Dec
    unit_code: str
    currency_code: str = "EUR"
    valid_from: datetime | None = None


class PriceOut(ApiModel):
    id: int
    product_id: int
    price_type: str
    amount: Dec
    currency_code: str
    unit_code: str
    valid_from: datetime
    valid_to: datetime | None = None


class LotReceiptIn(BaseModel):
    lot_code: str = Field(min_length=1, max_length=80)
    product_id: int
    supplier_id: int | None = None
    quantity: Dec
    unit_code: str
    unit_cost: Dec
    received_at: datetime | None = None
    expiry_date: date | None = None


class LotOut(ApiModel):
    id: int
    lot_code: str
    product_id: int
    product_code: str | None = None
    product_name: str | None = None
    supplier_id: int | None = None
    lot_origin_type: str
    status: str
    unit_code: str
    initial_quantity: Dec
    on_hand_quantity: Dec
    unit_cost: Dec | None = None
    expiry_date: date | None = None
    received_at: datetime | None = None
    location_code: str
    is_blocked: bool


class MovementOut(ApiModel):
    id: int
    lot_id: int
    lot_code: str | None = None
    product_id: int
    direction: str
    movement_type: str
    quantity: Dec
    unit_code: str
    source_type: str
    source_id: int
    location_code: str | None = None
    reverses_movement_id: int | None = None
    occurred_at: datetime
    created_by: int | None = None


class AdjustmentIn(BaseModel):
    lot_id: int
    direction: Literal["IN", "OUT"]
    movement_type: Literal["ADJUSTMENT", "WASTE"] = "ADJUSTMENT"
    quantity: Dec
    reason: str = Field(min_length=3, max_length=500)


class TransferIn(BaseModel):
    lot_id: int
    quantity: Dec
    to_location: str = Field(min_length=1, max_length=40)
    reason: str | None = None
