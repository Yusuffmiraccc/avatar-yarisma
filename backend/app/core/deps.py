from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import permissions_for
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

DB = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    email: str
    display_name: str
    roles: list[str]
    permissions: frozenset[str]


def get_current_user(
    request: Request,
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if creds is None:
        raise AppError(401, "UNAUTHENTICATED", "Kimlik doğrulama gerekli.")
    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise AppError(401, "UNAUTHENTICATED", "Geçersiz veya süresi dolmuş token.")
    user = db.get(User, int(payload["sub"]))
    # Her istekte aktiflik ve token sürümü kontrolü (KNOWN_GAPS: disabled user).
    if user is None or not user.is_active or user.token_version != payload.get("ver"):
        raise AppError(401, "UNAUTHENTICATED", "Oturum geçersiz.")
    roles = [r.code for r in user.roles]
    cu = CurrentUser(user.id, user.email, user.display_name, roles, permissions_for(roles))
    request.state.user_id = user.id
    return cu


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require(permission: str):
    def checker(user: CurrentUserDep) -> CurrentUser:
        if permission not in user.permissions:
            raise AppError(403, "FORBIDDEN", "Bu işlem için yetkiniz yok.", {"required": permission})
        return user

    checker.permission = permission  # izin matrisi testi / belge üretimi için
    return Depends(checker)
