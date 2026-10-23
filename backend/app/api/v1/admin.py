from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update

from app.api.v1.catalog import lot_out_many
from app.core.deps import DB, require
from app.core.errors import bad_request, conflict, not_found, request_id_of
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Customer,
    InventoryBalance,
    Lot,
    LotBlock,
    Product,
    ProductPrice,
    RefreshSession,
    Role,
    User,
)
from app.models.types import utcnow
from app.schemas.catalog import CustomerOut, LotOut, ProductOut
from app.schemas.common import ApiModel, Dec, Page, PageParams, normalize_utc, paginate
from app.services import audit

router = APIRouter(tags=["admin"])
PP = Annotated[PageParams, Depends()]
MIN_PASSWORD = 10


class UserIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=MIN_PASSWORD, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)
    roles: list[str] = Field(min_length=1)


class UserPatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    roles: list[str] | None = None


class PasswordIn(BaseModel):
    new_password: str = Field(min_length=MIN_PASSWORD, max_length=200)


class UserAdminOut(ApiModel):
    id: int
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime


def _user_out(u: User) -> UserAdminOut:
    return UserAdminOut(id=u.id, email=u.email, display_name=u.display_name, is_active=u.is_active,
                        roles=[r.code for r in u.roles], created_at=u.created_at)


def _roles(db, codes: list[str]) -> list[Role]:
    unknown = set(codes) - set(ROLE_PERMISSIONS)
    if unknown:
        raise bad_request("Bilinmeyen rol.", {"roles": sorted(unknown)})
    return list(db.scalars(select(Role).where(Role.code.in_(codes))))


def _revoke_sessions(db, user_id: int) -> None:
    db.execute(update(RefreshSession).where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


@router.get("/users", response_model=Page[UserAdminOut])
def list_users(db: DB, p: PP, _=require("users:manage")):
    res = paginate(db, select(User).order_by(User.id), p)
    res["items"] = [_user_out(u) for u in res["items"]]
    return res


@router.post("/users", response_model=UserAdminOut, status_code=201)
def create_user(body: UserIn, request: Request, db: DB, admin=require("users:manage")):
    email = body.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise conflict("CONFLICT", "Bu e-posta zaten kayıtlı.")
    u = User(email=email, password_hash=hash_password(body.password), display_name=body.display_name, is_active=True)
    u.roles = _roles(db, body.roles)
    db.add(u)
    db.flush()
    audit.record(db, actor_id=admin.id, action="USER_CREATED", entity_type="user", entity_id=u.id,
                 request_id=request_id_of(request), details={"roles": body.roles})
    return _user_out(u)


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def patch_user(user_id: int, body: UserPatch, request: Request, db: DB, admin=require("users:manage")):
    u = db.get(User, user_id)
    if u is None:
        raise not_found("Kullanıcı", user_id)
    if body.display_name is not None:
        u.display_name = body.display_name
    if body.roles is not None:
        u.roles = _roles(db, body.roles)
        u.token_version += 1  # eski access token'lar geçersiz
    if body.is_active is not None and body.is_active != u.is_active:
        if user_id == admin.id and not body.is_active:
            raise bad_request("Kendi hesabınızı devre dışı bırakamazsınız.")
        u.is_active = body.is_active
        u.token_version += 1
        if not body.is_active:
            _revoke_sessions(db, u.id)
    db.flush()
    audit.record(db, actor_id=admin.id, action="USER_UPDATED", entity_type="user", entity_id=u.id,
                 request_id=request_id_of(request), details=body.model_dump(exclude_unset=True))
    return _user_out(u)


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_password(user_id: int, body: PasswordIn, request: Request, db: DB, admin=require("users:manage")):
    u = db.get(User, user_id)
    if u is None:
        raise not_found("Kullanıcı", user_id)
    u.password_hash, u.token_version = hash_password(body.new_password), u.token_version + 1
    _revoke_sessions(db, u.id)
    audit.record(db, actor_id=admin.id, action="USER_PASSWORD_RESET", entity_type="user", entity_id=u.id,
                 request_id=request_id_of(request))


class AuditOut(ApiModel):
    id: int
    actor_user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int
    occurred_at: datetime
    request_id: str | None = None
    details: dict | None = None


@router.get("/audit-events", response_model=Page[AuditOut])
def audit_events(db: DB, p: PP, entity_type: str | None = None, entity_id: int | None = None, action: str | None = None,
                 actor_user_id: int | None = None, _=require("audit:read")):
    """Geçmişe dönük inceleme: kim, ne zaman, hangi kayıt üzerinde ne yaptı."""
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc())
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor_user_id is not None:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    return paginate(db, stmt, p)


class SellableLot(LotOut):
    sale_price: Dec | None = None


@router.get("/sync/catalog")
def sync_catalog(db: DB, updated_after: datetime | None = None, user=require("catalog:read")):
    """Android SQLite önbelleği için tek çağrılık anlık görüntü. Sunucu doğruluk kaynağıdır; satış öncesi yine doğrulanır.

    products/customers: updated_after'tan sonra değişenler. sellable_lots: stokta olan ve bloke olmayan lotlar.
    blocked_lot_ids: önbellekten çıkarılması gereken bloke lotlar. Dönen server_time bir sonraki çağrıda kullanılır.
    """
    pstmt, cstmt = select(Product), select(Customer)
    updated_after = normalize_utc(updated_after)
    if updated_after:
        pstmt = pstmt.where(or_(Product.updated_at >= updated_after, Product.created_at >= updated_after))
        cstmt = cstmt.where(or_(Customer.updated_at >= updated_after, Customer.created_at >= updated_after))
    price = {}
    for pr in db.scalars(select(ProductPrice).where(ProductPrice.price_type == "SALE", ProductPrice.valid_to.is_(None))):
        price[pr.product_id] = pr.amount
    lots = db.scalars(select(Lot).join(InventoryBalance, InventoryBalance.lot_id == Lot.id)
                      .where(InventoryBalance.on_hand_quantity > 0,
                             ~select(LotBlock.id).where(LotBlock.lot_id == Lot.id, LotBlock.unblocked_at.is_(None)).exists())
                      .order_by(Lot.id)).all()
    blocked = [r for r in db.scalars(select(LotBlock.lot_id).where(LotBlock.unblocked_at.is_(None)).distinct())]
    return {
        "server_time": utcnow().isoformat(timespec="microseconds") + "Z",
        "products": [ProductOut.model_validate(p).model_dump(mode="json") for p in db.scalars(pstmt.order_by(Product.id))],
        "customers": [CustomerOut.model_validate(c).model_dump(mode="json") for c in db.scalars(cstmt.order_by(Customer.id))],
        "sellable_lots": [SellableLot(**row.model_dump(exclude_unset=True),
                                        sale_price=price.get(lot_obj.product_id)).model_dump(mode="json", exclude_unset=True)
                          for lot_obj, row in zip(lots, lot_out_many(db, lots, include_cost="costs:read" in user.permissions), strict=True)],
        "blocked_lot_ids": blocked,
    }
