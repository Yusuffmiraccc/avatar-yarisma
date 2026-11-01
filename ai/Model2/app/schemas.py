from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


MODEL_B_FEATURES = ("hayvan_turu", "karkas_agirligi_kg")
MODEL_B_TARGETS = (
    "but_kg", "sirt_kg", "omuz_kg", "kaburga_kg", "kiyma_kg",
    "yan_urun_kg", "kemik_yag_sinir_kg", "fire_kg",
)


class CarcassCutsPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    hayvan_turu: str = Field(pattern="^(kuzu|koyun|dana)$")
    karkas_agirligi_kg: float = Field(gt=0, le=1000, strict=True)


class CarcassCutsPredictionResponse(BaseModel):
    predicted_cuts_kg: dict[str, float]
    prediction_id: str
    prediction_created_at_utc: str
    model_version: str
    data_version: str
    source_type: str
    production_ready: bool
    model_notice: str


class CarcassCutsExperimentalPredictionResponse(BaseModel):
    predicted_cuts_kg: dict[str, float]
    prediction_id: str
    prediction_created_at_utc: str
    model_version: str
    data_version: str
    source_type: str = "synthetic"
    production_ready: bool = False
    experimental: bool = True
    model_notice: str


class Model2StatusResponse(BaseModel):
    service: str
    model_b_production_ready: bool
    model_b_model_version: str | None
    model_b_data_version: str | None
    model_b_source_type: str | None
    model_b_candidate_available: bool
    model_b_candidate_model_version: str | None
    model_b_candidate_data_version: str | None
    model_b_candidate_source_type: str | None
    model_b_candidate_production_ready: bool | None
    model_b_feature_columns: list[str]
    model_b_target_columns: list[str]
    model_notice: str


class CarcassCutsActualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    prediction_id: str = Field(min_length=36, max_length=36, pattern="^[0-9a-fA-F-]{36}$")
    actual_cuts_kg: dict[str, float]
    measured_at_utc: datetime

    @field_validator("actual_cuts_kg", mode="before")
    @classmethod
    def validate_actual_weight_map(cls, values):
        if not isinstance(values, dict):
            raise ValueError("Parça ağırlıkları nesne olmalıdır")
        for key, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} kg değeri sayısal olmalıdır")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} kg değeri sonlu ve negatif olmayan olmalıdır")
        return values

    @field_validator("measured_at_utc")
    @classmethod
    def require_timezone_on_measurement_time(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Ölçüm zamanı saat dilimi bilgisi içermelidir")
        return value


class CarcassCutsActualResponse(BaseModel):
    prediction_id: str
    recorded_at_utc: str
    measured_at_utc: str
    actual_source_type: str


class StoredCarcassCutsEvaluationResponse(BaseModel):
    prediction_id: str
    model_version: str
    data_version: str
    source_type: str
    is_experimental: bool = False
    prediction_created_at_utc: str
    actual_source_type: str
    actual_measured_at_utc: str
    actual_recorded_at_utc: str
    comparison: dict[str, dict[str, float]]
    deviation_convention: str
