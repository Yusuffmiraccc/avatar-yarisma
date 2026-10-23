import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("avatar")

HTTP_CODES = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    429: "RATE_LIMITED",
}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str, ident: object) -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} bulunamadı.", {"id": str(ident)})


def conflict(code: str, message: str, details: dict | list | None = None) -> AppError:
    return AppError(409, code, message, details)


def bad_request(message: str, details: dict | list | None = None) -> AppError:
    return AppError(400, "VALIDATION_ERROR", message, details)


def invalid_state(message: str, details: dict | list | None = None) -> AppError:
    return AppError(409, "INVALID_STATE_TRANSITION", message, details)


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid4())


def _envelope(request: Request, status: int, code: str, message: str, details=None) -> JSONResponse:
    error: dict = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    rid = request_id_of(request)
    return JSONResponse(status_code=status, content={"error": error, "request_id": rid}, headers={"X-Request-ID": rid})


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request.state.request_id = validated_request_id(supplied)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def validated_request_id(supplied: str) -> str:
    """Accept short, printable correlation IDs only; otherwise issue a server UUID."""
    return supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied) else str(uuid4())


def register_error_handlers(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _envelope(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return _envelope(request, 400, "VALIDATION_ERROR", "İstek verileri doğrulanamadı.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return _envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("unhandled error request_id=%s", request_id_of(request))
        return _envelope(request, 500, "INTERNAL_ERROR", "Beklenmeyen bir sunucu hatası oluştu.")
