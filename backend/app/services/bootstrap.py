"""Referans veri (roller, birimler) ve kullanıcı oluşturma. Idempotent: tekrar çalıştırılabilir."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ROLE_NAMES
from app.core.security import hash_password
from app.models import Role, Unit, UnitConversion, User

UNITS = [
    ("KG", "Kilogram", "MASS"), ("G", "Gram", "MASS"),
    ("PACK", "Paket", "COUNT"), ("PCS", "Adet", "COUNT"),
]
CONVERSIONS = [("KG", "G", Decimal(1000)), ("G", "KG", Decimal("0.001"))]


def seed_reference(db: Session) -> None:
    for code, name in ROLE_NAMES.items():
        if db.scalar(select(Role).where(Role.code == code)) is None:
            db.add(Role(code=code, name=name))
    for code, name, dim in UNITS:
        if db.get(Unit, code) is None:
            db.add(Unit(code=code, name=name, dimension=dim))
    db.flush()
    for a, b, f in CONVERSIONS:
        exists = db.scalar(select(UnitConversion).where(UnitConversion.from_unit_code == a,
                                                        UnitConversion.to_unit_code == b))
        if exists is None:
            db.add(UnitConversion(from_unit_code=a, to_unit_code=b, factor=f))
    db.flush()


def create_user(db: Session, email: str, password: str, display_name: str, roles: list[str]) -> User:
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(password), display_name=display_name, is_active=True)
        db.add(user)
        db.flush()
    wanted = db.scalars(select(Role).where(Role.code.in_(roles))).all()
    user.roles = list(wanted)
    db.flush()
    return user
