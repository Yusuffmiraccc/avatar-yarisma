from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import BigId, created_at, fk, pk, ts, updated_at


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = pk()
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Access token geçersiz kılma: parola/rol/aktiflik değişince artırılır.
    token_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime | None] = updated_at()
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = pk()
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(BigId, ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigId, ForeignKey("roles.id"), primary_key=True)
    created_at: Mapped[datetime] = created_at()


class RefreshSession(Base):
    """refresh rotation, hash saklanır, reuse'da aile iptali."""

    __tablename__ = "refresh_sessions"
    id: Mapped[int] = pk()
    user_id: Mapped[int] = fk("users.id")
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = ts(nullable=False)
    revoked_at: Mapped[datetime | None] = ts()
    replaced_by_id: Mapped[int | None] = fk("refresh_sessions.id", nullable=True)
    created_at: Mapped[datetime] = created_at()
