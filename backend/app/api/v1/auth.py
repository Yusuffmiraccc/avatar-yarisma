from fastapi import APIRouter, Request, Response

from app.core.deps import DB, CurrentUserDep
from app.core.errors import request_id_of
from app.core.permissions import permissions_for
from app.schemas.auth import LoginIn, RefreshIn, TokenOut, UserOut
from app.services import auth as svc

router = APIRouter(prefix="/auth", tags=["auth"])


def _out(user, tokens) -> TokenOut:
    roles = [r.code for r in user.roles]
    return TokenOut(**tokens, user=UserOut(id=user.id, email=user.email, display_name=user.display_name,
                                           roles=roles, permissions=sorted(permissions_for(roles))))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: DB):
    user, tokens = svc.login(db, body.email, body.password, request_id_of(request))
    return _out(user, tokens)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, request: Request, db: DB):
    user, tokens = svc.refresh(db, body.refresh_token, request_id_of(request))
    return _out(user, tokens)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: DB):
    svc.logout(db, body.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUserDep):
    return UserOut(id=user.id, email=user.email, display_name=user.display_name, roles=user.roles,
                   permissions=sorted(user.permissions))
