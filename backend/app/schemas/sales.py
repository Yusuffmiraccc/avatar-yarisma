from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, Dec


class SaleLineIn(BaseModel):
    lot_id: int
    quantity: Dec
    unit_price: Dec | None = None  # verilmezse ürünün geçerli SALE fiyatı kullanılır
    override_reason: str | None = Field(default=None, min_length=5, max_length=500)


class SaleIn(BaseModel):
    customer_id: int
    sold_at: datetime | None = None
    lines: list[SaleLineIn] = Field(min_length=1)


class SaleLineOut(ApiModel):
    id: int
    line_number: int
    product_id: int
    lot_id: int
    lot_code: str | None = None
    quantity: Dec
    unit_code: str
    unit_price: Dec
    line_total: Dec
    stock_movement_id: int | None = None


class SaleOut(ApiModel):
    id: int
    sale_code: str
    customer_id: int | None = None
    shipment_id: int | None = None
    status: str
    sold_at: datetime
    currency_code: str
    total_amount: Dec
    lines: list[SaleLineOut] = Field(default_factory=list)


class ShipmentLineIn(BaseModel):
    lot_id: int
    quantity: Dec


class ShipmentIn(BaseModel):
    shipment_code: str = Field(min_length=1, max_length=80)
    customer_id: int
    notes: str | None = Field(default=None, max_length=1000)
    lines: list[ShipmentLineIn] = Field(min_length=1)


class ShipmentLineOut(ApiModel):
    id: int
    line_number: int
    product_id: int
    lot_id: int
    lot_code: str | None = None
    quantity: Dec
    unit_code: str
    stock_movement_id: int | None = None


class ShipmentOut(ApiModel):
    id: int
    shipment_code: str
    customer_id: int
    customer_name: str | None = None
    status: str
    shipped_at: datetime | None = None
    notes: str | None = None
    lines: list[ShipmentLineOut] = Field(default_factory=list)
