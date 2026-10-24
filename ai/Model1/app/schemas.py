import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductionPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    Et_girdi_kg: float = Field(gt=0, le=100000)
    Kuyruk_yagi_girdi_kg: float = Field(ge=0, le=100000)
    Baharat_girdi_kg: float = Field(ge=0, le=10000)
    Tuz_girdi_kg: float = Field(ge=0, le=10000)
    Diger_kucuk_girdi_kg: float = Field(ge=0, le=10000)
    Kilif_metre: float = Field(ge=0, le=100000)

    Et_fiyat_TL_kg: float = Field(gt=0, le=100000)
    Kuyruk_yagi_fiyat_TL_kg: float = Field(ge=0, le=100000)
    Baharat_fiyat_TL_kg: float = Field(ge=0, le=100000)
    Tuz_fiyat_TL_kg: float = Field(ge=0, le=100000)
    Kilif_fiyat_TL_m: float = Field(ge=0, le=100000)
    Fason_birim_bedel_TL_kg_girdi: float = Field(ge=0, le=100000)

    # Optional legacy/planning fields. These are not used by Scenario A models.
    Kuruma_kaybi_pct: float | None = Field(default=None, ge=0, le=100)
    Ayiklama_fire_pct: float | None = Field(default=None, ge=0, le=100)
    Iscilik_saati: float | None = Field(default=None, ge=0, le=100000)
    Iscilik_maliyeti_TL_saat: float = Field(ge=0, le=100000)
    Elektrik_kWh: float | None = Field(default=None, ge=0, le=1000000)
    Elektrik_fiyati_TL_kWh: float = Field(ge=0, le=100000)
    Ambalaj_TL_kg_net_urun: float = Field(ge=0, le=100000)
    Genel_gider_TL: float | None = Field(default=None, ge=0, le=100000000)

    Bolge: str
    Recete_profili: str
    Isleme_modeli: str

    @field_validator("Bolge")
    @classmethod
    def validate_region(cls, value):
        allowed = {"Akdeniz", "Doğu Anadolu", "Ege", "Güneydoğu Anadolu", "Karadeniz", "Marmara", "İç Anadolu"}
        if value not in allowed:
            raise ValueError("Bilinmeyen bölge kategorisi")
        return value

    @field_validator("Recete_profili")
    @classmethod
    def validate_recipe_profile(cls, value):
        if value not in {"ERZURUM_CI", "MEB_STANDART"}:
            raise ValueError("Bilinmeyen reçete profili")
        return value

    @field_validator("Isleme_modeli")
    @classmethod
    def validate_processing_model(cls, value):
        if value not in {"Fason", "Kurum içi"}:
            raise ValueError("Bilinmeyen işleme modeli")
        return value


class ProductionEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    predicted_net_output_kg: float = Field(ge=0)
    actual_net_output_kg: float = Field(gt=0)
    predicted_ekp_tl_per_kg: float = Field(ge=0)
    actual_total_cost_tl: float = Field(gt=0)

    @property
    def actual_ekp_tl_per_kg(self) -> float:
        return self.actual_total_cost_tl / self.actual_net_output_kg


class ProductionPredictionResponse(BaseModel):
    predicted_net_output_kg: float
    predicted_ekp_tl_per_kg: float
    model_notice: str


class ProductionEvaluationResponse(BaseModel):
    predicted_net_output_kg: float
    actual_net_output_kg: float
    yield_deviation_kg: float
    predicted_ekp_tl_per_kg: float
    actual_total_cost_tl: float
    actual_ekp_tl_per_kg: float
    ekp_deviation_tl_per_kg: float
    deviation_convention: str


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
    prediction_created_at_utc: str
    actual_source_type: str
    actual_measured_at_utc: str
    actual_recorded_at_utc: str
    comparison: dict[str, dict[str, float]]
    deviation_convention: str
