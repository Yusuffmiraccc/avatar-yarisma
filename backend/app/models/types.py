from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import mapped_column

BigId = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql").with_variant(Integer, "sqlite")
Money = Numeric(19, 4)
Qty = Numeric(19, 6)
UtcDateTime = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def pk():
    return mapped_column(BigId, primary_key=True, autoincrement=True)


def fk(target: str, *, nullable: bool = False, **kw):
    return mapped_column(BigId, ForeignKey(target), nullable=nullable, **kw)


def unit_fk(*, nullable: bool = False):
    return mapped_column(String(16), ForeignKey("units.code"), nullable=nullable)


def created_at():
    return mapped_column(UtcDateTime, nullable=False, default=utcnow)


def updated_at():
    return mapped_column(UtcDateTime, nullable=True, onupdate=utcnow)


def ts(nullable: bool = True):
    return mapped_column(UtcDateTime, nullable=nullable)
