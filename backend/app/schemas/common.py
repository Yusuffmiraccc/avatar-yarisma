from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    field_serializer,
)

T = TypeVar("T")


def _no_float(v):
    if isinstance(v, (float, bool)):
        raise ValueError("Para ve miktar alanları JSON string olarak gönderilmelidir.")
    return v


def _fmt(v: Decimal) -> str:
    return format(v, "f")


def normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


# Para ve miktar: girişte string/Decimal (float reddedilir), çıkışta string.
Dec = Annotated[Decimal, BeforeValidator(_no_float), PlainSerializer(_fmt, return_type=str, when_used="json")]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _dt(self, v):  # UTC ISO-8601 'Z'
        if isinstance(v, datetime):
            normalized = v.astimezone(UTC).replace(tzinfo=None) if v.tzinfo else v
            return normalized.isoformat(timespec="microseconds") + "Z"
        return v


class Page(ApiModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class PageParams:
    def __init__(self, page: int = 1, page_size: int = 50, updated_after: datetime | None = None):
        self.page = max(page, 1)
        self.page_size = min(max(page_size, 1), 100)
        self.updated_after = normalize_utc(updated_after)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(db, stmt, params: PageParams, count_stmt=None):
    from sqlalchemy import func, select

    total = db.scalar(count_stmt if count_stmt is not None else select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(params.offset).limit(params.page_size)).all()
    return {"items": rows, "page": params.page, "page_size": params.page_size, "total": total or 0}


__all__ = ["ApiModel", "Dec", "Field", "Page", "PageParams", "paginate"]


_COST_FIELDS = frozenset({
    "unit_cost", "cost_snapshot", "allocated_cost", "total_purchase_cost",
    "sellable_cost_total", "waste_cost_total", "allocated_total", "total_input_cost",
    "total_service_cost", "total_cost", "unit_cost_ekp", "unit_cost_ekp_display",
    "predicted_cost", "baseline_cost", "actual_cost", "stock_value", "value", "total_value",
    "ekp", "ekp_display", "vkp", "gross_profit_per_unit", "margin_percent", "gross_profit_total",
    "amount", "unit_price", "declared_unit_price", "stated_total", "lines_total", "extra_cost",
})

_COST_DIAGNOSTIC_CODES = frozenset({"SOURCE_COST_MISMATCH", "COST_INCREASE"})


def redact_cost_data(value):
    """Serialize a response and remove every known cost/profit field recursively."""
    data = jsonable_encoder(value)
    if isinstance(data, dict):
        diagnostic_code = data.get("code", data.get("alert_type"))
        if diagnostic_code in _COST_DIAGNOSTIC_CODES:
            # Cost diagnostics also embed amounts in prose and generic keys such as
            # computed_total/difference, which cannot safely be removed by key name.
            data["message"] = "Hassas maliyet verisi içeren bir tutarsızlık bulundu."
            if "details" in data:
                data["details"] = {}
        return {key: redact_cost_data(item) for key, item in data.items() if key not in _COST_FIELDS}
    if isinstance(data, list):
        return [redact_cost_data(item) for item in data]
    return data
