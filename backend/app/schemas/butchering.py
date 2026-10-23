from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, Dec

WasteReason = Literal["TRIMMING_LOSS", "BONE_WASTE", "CONTAMINATION", "SPOILAGE", "PROCESS_LOSS", "OTHER"]


class RecipeLineIn(BaseModel):
    product_id: int
    output_type: Literal["CUT", "BYPRODUCT", "WASTE"]
    expected_ratio: Dec


class RecipeIn(BaseModel):
    lines: list[RecipeLineIn] = Field(min_length=1)


class RecipeLineOut(ApiModel):
    product_id: int
    output_type: str
    expected_ratio: Dec


class RecipeOut(ApiModel):
    animal_type: str
    lines: list[RecipeLineOut]
    ratio_sum: Dec


class ButcheringOrderIn(BaseModel):
    order_code: str = Field(min_length=1, max_length=80)
    animal_type: str = Field(min_length=1, max_length=40)
    input_weight: Dec
    input_unit_code: str = "KG"
    total_purchase_cost: Dec
    declared_unit_price: Dec | None = None
    allocation_method: Literal["BY_WEIGHT", "BY_VALUE"] = "BY_WEIGHT"
    notes: str | None = Field(default=None, max_length=1000)


class ButcheringInputIn(BaseModel):
    lot_id: int
    quantity: Dec
    unit_code: str = "KG"


class WasteIn(BaseModel):
    input_lot_id: int | None = None
    actual_weight: Dec
    unit_code: str = "KG"
    reason_code: WasteReason
    notes: str | None = Field(default=None, max_length=1000)


class ButcheringOutputIn(BaseModel):
    product_id: int
    lot_code: str = Field(min_length=1, max_length=80)
    actual_weight: Dec
    unit_code: str = "KG"
    output_type: Literal["CUT", "BYPRODUCT"] = "CUT"
    expiry_date: date | None = None


class ButcheringCompleteIn(BaseModel):
    outputs: list[ButcheringOutputIn] = Field(min_length=1)
    variance_reason: str | None = Field(default=None, min_length=5, max_length=500)
    waste_unit_value: Dec | None = None  # yalnız BY_VALUE; onaylı fire değerlemesi


class BInputOut(ApiModel):
    id: int
    lot_id: int
    lot_code: str | None = None
    quantity: Dec
    unit_code: str
    cost_snapshot: Dec


class BOutputOut(ApiModel):
    id: int
    product_id: int
    lot_id: int
    lot_code: str | None = None
    output_type: str
    actual_weight: Dec
    unit_code: str
    expected_weight: Dec | None = None
    deviation_weight: Dec | None = None
    allocation_weight: Dec | None = None
    allocation_value: Dec | None = None
    allocated_cost: Dec
    unit_cost: Dec | None = None


class WasteOut(ApiModel):
    id: int
    input_lot_id: int
    actual_weight: Dec
    unit_code: str
    reason_code: str
    notes: str | None = None
    allocated_cost: Dec


class VarianceOut(ApiModel):
    variance_weight: Dec
    tolerance_weight: Dec
    reason_text: str
    allocated_cost: Dec
    approved_by: int


class Finding(BaseModel):
    code: str
    severity: str
    message: str
    details: dict


class ButcheringOrderOut(ApiModel):
    id: int
    order_code: str
    status: str
    animal_type: str
    input_weight: Dec
    input_unit_code: str
    total_purchase_cost: Dec
    declared_unit_price: Dec | None = None
    allocation_method: str
    weight_difference: Dec | None = None
    reversed_at: datetime | None = None
    reversal_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    inputs: list[BInputOut] = Field(default_factory=list)
    outputs: list[BOutputOut] = Field(default_factory=list)
    waste_records: list[WasteOut] = Field(default_factory=list)
    variance: VarianceOut | None = None
    findings: list[Finding] = Field(default_factory=list)
    sellable_cost_total: Dec | None = None
    waste_cost_total: Dec | None = None
    allocated_total: Dec | None = None
