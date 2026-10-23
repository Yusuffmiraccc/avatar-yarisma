from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, Dec


class ProductionOrderIn(BaseModel):
    order_code: str = Field(min_length=1, max_length=80)
    production_type: Literal["IN_HOUSE", "OUTSOURCED"] = "OUTSOURCED"
    supplier_id: int | None = None
    planned_quantity: Dec | None = None
    planned_unit_code: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ProductionInputIn(BaseModel):
    lot_id: int
    quantity: Dec
    unit_code: str


class ServiceCostIn(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    supplier_id: int | None = None
    quantity: Dec | None = None
    unit_price: Dec | None = None
    amount: Dec | None = None  # quantity+unit_price yoksa doğrudan tutar


class OutputIn(BaseModel):
    product_id: int
    lot_code: str = Field(min_length=1, max_length=80)
    quantity: Dec
    unit_code: str
    expiry_date: date | None = None


class CompleteIn(BaseModel):
    outputs: list[OutputIn] = Field(min_length=1)


class InputOut(ApiModel):
    id: int
    lot_id: int
    lot_code: str | None = None
    product_id: int
    quantity: Dec
    unit_code: str
    unit_cost: Dec
    total_cost: Dec


class ServiceCostOut(ApiModel):
    id: int
    description: str
    quantity: Dec | None = None
    unit_price: Dec | None = None
    amount: Dec
    supplier_id: int | None = None


class OutputOut(ApiModel):
    id: int
    lot_id: int
    lot_code: str | None = None
    product_id: int
    quantity: Dec
    unit_code: str
    unit_cost: Dec | None = None


class ProductionOrderOut(ApiModel):
    id: int
    order_code: str
    production_type: str
    status: str
    supplier_id: int | None = None
    planned_quantity: Dec | None = None
    planned_unit_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    inputs: list[InputOut] = Field(default_factory=list)
    service_costs: list[ServiceCostOut] = Field(default_factory=list)
    outputs: list[OutputOut] = Field(default_factory=list)
    total_input_cost: Dec | None = None
    total_service_cost: Dec | None = None
    total_cost: Dec | None = None
    actual_output_quantity: Dec | None = None
    quantity_difference: Dec | None = None  # gerçekleşen − planlanan (mamul kabulü miktar farkı)
    reversed_at: datetime | None = None
    reversal_reason: str | None = None
    unit_cost_ekp: Dec | None = None
    unit_cost_ekp_display: Dec | None = None
    input_mass_kg: Dec | None = None
    yield_ratio: Dec | None = None
    vkp: Dec | None = None
    gross_profit_per_unit: Dec | None = None
    margin_percent: Dec | None = None
    gross_profit_total: Dec | None = None
