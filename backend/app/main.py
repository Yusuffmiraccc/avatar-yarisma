import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.body_limit import UploadBodyLimitMiddleware
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging_mw import AccessLogMiddleware
from app.db.session import engine
from app.services import auth as auth_service

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app(app_settings=settings) -> FastAPI:
    local = app_settings.environment == "local"
    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        openapi_url=f"{app_settings.api_v1_prefix}/openapi.json" if local else None,
        docs_url=f"{app_settings.api_v1_prefix}/docs" if local else None,
        redoc_url=f"{app_settings.api_v1_prefix}/redoc" if local else None,
    )
    register_error_handlers(application)
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in app_settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"], allow_headers=["*"],
        expose_headers=["X-Request-ID", "Idempotent-Replay"],
    )
    application.add_middleware(UploadBodyLimitMiddleware,
                               path=f"{app_settings.api_v1_prefix}/documents/extract-file",
                               max_body_bytes=5_000_000 + 128 * 1024)
    application.include_router(v1_router, prefix=app_settings.api_v1_prefix)

    @application.get("/health/live", tags=["system"])
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["system"])
    def ready():
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            if not auth_service.rate_limit_store_ready():
                return JSONResponse(status_code=503, content={"status": "unavailable"})
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ok"}

    return application


app = create_app()
