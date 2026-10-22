from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, field_serializer

T = TypeVar("T")


def _no_float(v):
    if isinstance(v, (float, bool)):
        raise ValueError("Para ve miktar alanları JSON string olarak gönderilmelidir.")
    return v


def _fmt(v: Decimal) -> str:
    return format(v, "f")


# Para ve miktar: girişte string/Decimal (float reddedilir), çıkışta string.
Dec = Annotated[Decimal, BeforeValidator(_no_float), PlainSerializer(_fmt, return_type=str, when_used="json")]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _dt(self, v):  # UTC ISO-8601 'Z'
        if isinstance(v, datetime):
            return v.replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"
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
        self.updated_after = updated_after

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(db, stmt, params: PageParams, count_stmt=None):
    from sqlalchemy import func, select

    total = db.scalar(count_stmt if count_stmt is not None else select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(params.offset).limit(params.page_size)).all()
    return {"items": rows, "page": params.page, "page_size": params.page_size, "total": total or 0}


__all__ = ["ApiModel", "Dec", "Field", "Page", "PageParams", "paginate"]
