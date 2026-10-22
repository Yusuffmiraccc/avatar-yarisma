import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("avatar.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Yöntem, yol, durum, süre, request_id, kullanıcı. Gövde, başlık ve token LOGLANMAZ."""

    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        log.info("%s %s -> %s %.1fms rid=%s user=%s", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - t0) * 1000, getattr(request.state, "request_id", "-"),
                 getattr(request.state, "user_id", "-"))
        return response
