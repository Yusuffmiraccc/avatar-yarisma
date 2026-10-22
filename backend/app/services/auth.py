import time
import uuid
from collections import defaultdict, deque
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_token, new_refresh_token, verify_password
from app.models import RefreshSession, User
from app.models.types import utcnow
from app.services import audit

_attempts: dict[str, deque] = defaultdict(deque)
MAX_ATTEMPTS, WINDOW = 10, 15 * 60  # tek süreçli demo için bellek içi; çok instance'ta paylaşımlı store gerekir.


def _rate_limit(key: str) -> None:
    now = time.monotonic()
    q = _attempts[key]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= MAX_ATTEMPTS:
        raise AppError(429, "RATE_LIMITED", "Çok fazla başarısız giriş denemesi. Daha sonra tekrar deneyin.")


def reset_rate_limits() -> None:
    _attempts.clear()


def _issue(db: Session, user: User, family_id: str) -> dict:
    raw, digest = new_refresh_token()
    s = get_settings()
    sess = RefreshSession(user_id=user.id, family_id=family_id, token_hash=digest,
                          expires_at=utcnow() + timedelta(days=s.refresh_token_days))
    db.add(sess)
    db.flush()
    access, expires_in = create_access_token(user.id, [r.code for r in user.roles], user.token_version)
    return {"access_token": access, "refresh_token": raw, "token_type": "bearer", "expires_in": expires_in,
            "_session": sess}


def login(db: Session, email: str, password: str, request_id: str | None) -> tuple[User, dict]:
    email = email.strip().lower()
    _rate_limit(email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        _attempts[email].append(time.monotonic())
        raise AppError(401, "UNAUTHENTICATED", "E-posta veya parola hatalı.")
    if not user.is_active:
        raise AppError(401, "UNAUTHENTICATED", "Hesap devre dışı.")
    _attempts.pop(email, None)
    tokens = _issue(db, user, uuid.uuid4().hex)
    tokens.pop("_session")
    audit.record(db, actor_id=user.id, action="AUTH_LOGIN", entity_type="user", entity_id=user.id, request_id=request_id)
    return user, tokens


def refresh(db: Session, raw_token: str, request_id: str | None) -> tuple[User, dict]:
    sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)).with_for_update())
    if sess is None:
        raise AppError(401, "UNAUTHENTICATED", "Geçersiz refresh token.")
    if sess.revoked_at is not None:
        # Reuse tespiti: tüm aileyi iptal et.
        db.execute(update(RefreshSession).where(RefreshSession.family_id == sess.family_id,
                                                RefreshSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
        db.commit()
        raise AppError(401, "UNAUTHENTICATED", "Refresh token yeniden kullanıldı; oturum iptal edildi.")
    if sess.expires_at < utcnow():
        raise AppError(401, "UNAUTHENTICATED", "Refresh token süresi doldu.")
    user = db.get(User, sess.user_id)
    if user is None or not user.is_active:
        raise AppError(401, "UNAUTHENTICATED", "Hesap devre dışı.")
    tokens = _issue(db, user, sess.family_id)
    new_sess = tokens.pop("_session")
    sess.revoked_at = utcnow()
    sess.replaced_by_id = new_sess.id
    audit.record(db, actor_id=user.id, action="AUTH_REFRESH", entity_type="user", entity_id=user.id, request_id=request_id)
    return user, tokens


def logout(db: Session, raw_token: str) -> None:
    sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)))
    if sess is not None:
        db.execute(update(RefreshSession).where(RefreshSession.family_id == sess.family_id,
                                                RefreshSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
