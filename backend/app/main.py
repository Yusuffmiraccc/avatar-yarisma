from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import engine

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", openapi_url=f"{settings.api_v1_prefix}/openapi.json",
              docs_url=f"{settings.api_v1_prefix}/docs")
import logging

from app.core.logging_mw import AccessLogMiddleware

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
register_error_handlers(app)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID", "Idempotent-Replay"])
app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.get("/health/live", tags=["system"])
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["system"])
def ready():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
