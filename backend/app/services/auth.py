import hashlib
import hmac
import ipaddress
import threading
import uuid
from datetime import timedelta

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_token, new_refresh_token, verify_password
from app.models import RefreshSession, User
from app.models.types import utcnow
from app.services import audit

_mem_lock = threading.Lock()
_mem_attempts: dict[str, int] = {}
_mem_inflight: dict[str, int] = {}
_redis_lock = threading.Lock()
_redis_client: Redis | None = None
_redis_url: str | None = None
_redis_available: bool | None = None

def _is_redis_available() -> bool:
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    url = get_settings().redis_url.get_secret_value()
    if url.startswith("memory://") or not url:
        _redis_available = False
        return False
    try:
        client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.ping()
        _redis_available = True
        return True
    except (RedisError, OSError):
        _redis_available = False
        return False
_KEY_PREFIX = "avatar:login-limit:v1:"
MAX_ATTEMPTS, IP_MAX_ATTEMPTS, WINDOW = 10, 50, 15 * 60
_DUMMY_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$a+35qKYnSjBwgJTFIYoJEw$cl6rhWyUvcUA81FYT+qpLZ1qAq/mzyG0myDRwikY/HQ"
REFRESH_RETRY_WINDOW = timedelta(seconds=10)

_RESERVE_SCRIPT = """
local bucket_count = #KEYS / 2
for i = 1, bucket_count do
  local failures = tonumber(redis.call('GET', KEYS[(i - 1) * 2 + 1]) or '0')
  local inflight = tonumber(redis.call('GET', KEYS[(i - 1) * 2 + 2]) or '0')
  if failures + inflight >= tonumber(ARGV[i]) then
    return 0
  end
end
for i = 1, bucket_count do
  local inflight_key = KEYS[(i - 1) * 2 + 2]
  redis.call('INCR', inflight_key)
  redis.call('EXPIRE', inflight_key, tonumber(ARGV[bucket_count + 1]))
end
return 1
"""

_FINISH_SCRIPT = """
local bucket_count = #KEYS / 2
for i = 1, bucket_count do
  local inflight_key = KEYS[(i - 1) * 2 + 2]
  local value = tonumber(redis.call('GET', inflight_key) or '0')
  if value > 0 then
    value = redis.call('DECR', inflight_key)
  end
  if value <= 0 then
    redis.call('DEL', inflight_key)
  else
    redis.call('EXPIRE', inflight_key, tonumber(ARGV[2]))
  end
  if ARGV[1] == '1' then
    local failure_key = KEYS[(i - 1) * 2 + 1]
    redis.call('INCR', failure_key)
    redis.call('EXPIRE', failure_key, tonumber(ARGV[2]))
  end
end
if ARGV[3] == '1' then
  redis.call('DEL', KEYS[1])
end
return 1
"""


def _client_ip(request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    trusted = []
    for value in get_settings().trusted_proxy_ips.split(","):
        try:
            trusted.append(ipaddress.ip_network(value.strip(), strict=False))
        except ValueError:
            continue
    if not any(peer_ip in network for network in trusted):
        return peer
    chain = request.headers.get("x-forwarded-for", "").split(",")
    try:
        hops = [ipaddress.ip_address(value.strip()) for value in chain if value.strip()]
    except ValueError:
        return peer
    for hop in reversed(hops):
        if not any(hop in network for network in trusted):
            return str(hop)
    return str(hops[0]) if hops else peer


def _redis() -> Redis:
    global _redis_client, _redis_url
    url = get_settings().redis_url.get_secret_value()
    with _redis_lock:
        if _redis_client is None or _redis_url != url:
            _redis_client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
            _redis_url = url
        return _redis_client


def _storage_keys(keys: list[str]) -> list[str]:
    secret = get_settings().jwt_secret_key.get_secret_value().encode()
    return [
        _KEY_PREFIX + hmac.new(secret, key.encode(), hashlib.sha256).hexdigest() + suffix
        for key in keys
        for suffix in (":failures", ":inflight")
    ]


def _rate_limit_unavailable(exc: RedisError) -> AppError:
    return AppError(503, "SERVICE_UNAVAILABLE", "Kimlik doğrulama şu anda kullanılamıyor.")


def rate_limit_store_ready() -> bool:
    if not _is_redis_available():
        return True
    try:
        return bool(_redis().ping())
    except (RedisError, OSError):
        return False


def _reserve_attempt(keys: list[str]) -> None:
    if not _is_redis_available():
        with _mem_lock:
            for k in keys:
                limit = IP_MAX_ATTEMPTS if k.startswith("ip:") else MAX_ATTEMPTS
                if _mem_attempts.get(k, 0) + _mem_inflight.get(k, 0) >= limit:
                    raise AppError(429, "RATE_LIMITED", "Çok fazla başarısız giriş denemesi. Daha sonra tekrar deneyin.")
            for k in keys:
                _mem_inflight[k] = _mem_inflight.get(k, 0) + 1
        return

    storage_keys = _storage_keys(keys)
    limits = [IP_MAX_ATTEMPTS if key.startswith("ip:") else MAX_ATTEMPTS for key in keys]
    try:
        allowed = _redis().eval(_RESERVE_SCRIPT, len(storage_keys), *storage_keys, *limits, WINDOW)
    except (RedisError, OSError) as exc:
        raise _rate_limit_unavailable(exc) from exc
    if not allowed:
        raise AppError(429, "RATE_LIMITED", "Çok fazla başarısız giriş denemesi. Daha sonra tekrar deneyin.")


def _finish_attempt(keys: list[str], *, failed: bool, successful: bool = False) -> None:
    if not _is_redis_available():
        with _mem_lock:
            for k in keys:
                if k in _mem_inflight:
                    _mem_inflight[k] = max(0, _mem_inflight[k] - 1)
            if successful:
                for k in keys:
                    _mem_attempts.pop(k, None)
                    _mem_inflight.pop(k, None)
            elif failed:
                for k in keys:
                    _mem_attempts[k] = _mem_attempts.get(k, 0) + 1
        return

    try:
        storage_keys = _storage_keys(keys)
        _redis().eval(_FINISH_SCRIPT, len(storage_keys), *storage_keys, int(failed), WINDOW, int(successful))
    except (RedisError, OSError) as exc:
        raise _rate_limit_unavailable(exc) from exc


def _record_failures(keys: list[str]) -> None:
    if not _is_redis_available():
        with _mem_lock:
            for k in keys:
                _mem_attempts[k] = _mem_attempts.get(k, 0) + 1
        return

    try:
        client = _redis()
        for key in _storage_keys(keys)[::2]:
            with client.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, WINDOW)
                pipe.execute()
    except (RedisError, OSError) as exc:
        raise _rate_limit_unavailable(exc) from exc


def reset_rate_limits() -> None:
    with _mem_lock:
        _mem_attempts.clear()
        _mem_inflight.clear()
    if _is_redis_available():
        try:
            client = _redis()
            for key in client.scan_iter(f"{_KEY_PREFIX}*"):
                client.delete(key)
        except (RedisError, OSError):
            pass


def _issue(db: Session, user: User, family_id: str, raw_refresh_token: str | None = None) -> dict:
    raw, digest = new_refresh_token() if raw_refresh_token is None else (raw_refresh_token, hash_token(raw_refresh_token))
    s = get_settings()
    sess = RefreshSession(user_id=user.id, family_id=family_id, token_hash=digest,
                          expires_at=utcnow() + timedelta(days=s.refresh_token_days))
    db.add(sess)
    db.flush()
    access, expires_in = create_access_token(user.id, [r.code for r in user.roles], user.token_version)
    return {"access_token": access, "refresh_token": raw, "token_type": "bearer", "expires_in": expires_in,
            "_session": sess}


def login(db: Session, email: str, password: str, request_id: str | None, request=None) -> tuple[User, dict]:
    email = email.strip().lower()
    ip = _client_ip(request) if request is not None else "unknown"
    keys = [f"pair:{ip}:{email}", f"ip:{ip}"]
    _reserve_attempt(keys)
    failed = False
    successful = False
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            failed = True
            raise AppError(401, "UNAUTHENTICATED", "E-posta veya parola hatalı.")
        if not verify_password(password, user.password_hash):
            failed = True
            raise AppError(401, "UNAUTHENTICATED", "E-posta veya parola hatalı.")
        if not user.is_active:
            raise AppError(401, "UNAUTHENTICATED", "Hesap devre dışı.")
        tokens = _issue(db, user, uuid.uuid4().hex)
        tokens.pop("_session")
        audit.record(db, actor_id=user.id, action="AUTH_LOGIN", entity_type="user", entity_id=user.id, request_id=request_id)
        successful = True
        return user, tokens
    finally:
        _finish_attempt(keys, failed=failed, successful=successful)


def refresh(db: Session, raw_token: str, request_id: str | None) -> tuple[User, dict]:
    sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)).with_for_update())
    if sess is None:
        raise AppError(401, "UNAUTHENTICATED", "Geçersiz refresh token.")
    if sess.revoked_at is not None:
        now = utcnow()
        if sess.replaced_by_id is not None and now <= sess.revoked_at + REFRESH_RETRY_WINDOW:
            parent = sess
            successor = db.get(RefreshSession, sess.replaced_by_id)
            while (successor is not None and successor.revoked_at is not None
                   and successor.replaced_by_id is not None):
                parent = successor
                successor = db.get(RefreshSession, successor.replaced_by_id)
            user = db.get(User, sess.user_id)
            if (successor is not None and successor.revoked_at is None and successor.expires_at >= now
                    and user is not None and user.is_active):
                access, expires_in = create_access_token(user.id, [r.code for r in user.roles], user.token_version)
                return user, {"access_token": access, "refresh_token": _retry_token(parent),
                              "token_type": "bearer", "expires_in": expires_in}
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
    from sqlalchemy.exc import IntegrityError
    try:
        tokens = _issue(db, user, sess.family_id, raw_refresh_token=_retry_token(sess))
        new_sess = tokens.pop("_session")
        sess.revoked_at = utcnow()
        sess.replaced_by_id = new_sess.id
        db.flush()
    except IntegrityError:
        db.rollback()
        # Concurrency race: the competing request won and created the successor
        sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)))
        if sess is not None and sess.revoked_at is not None and sess.replaced_by_id is not None:
            successor = db.get(RefreshSession, sess.replaced_by_id)
            if successor is not None and successor.revoked_at is None and successor.expires_at >= utcnow():
                access, expires_in = create_access_token(user.id, [r.code for r in user.roles], user.token_version)
                return user, {"access_token": access, "refresh_token": _retry_token(sess),
                              "token_type": "bearer", "expires_in": expires_in}
        raise
    audit.record(db, actor_id=user.id, action="AUTH_REFRESH", entity_type="user", entity_id=user.id, request_id=request_id)
    return user, tokens


def _retry_token(sess: RefreshSession) -> str:
    """Deterministic successor permits a short, safe retry without storing raw bearer tokens."""
    secret = get_settings().jwt_secret_key.get_secret_value().encode()
    message = f"avatar-refresh-retry:{sess.family_id}:{sess.id}:{sess.token_hash}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def logout(db: Session, raw_token: str) -> None:
    sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)))
    if sess is not None:
        db.execute(update(RefreshSession).where(RefreshSession.family_id == sess.family_id,
                                                RefreshSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
