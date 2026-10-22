from fastapi import APIRouter

from app.api.v1 import (admin, ai, alerts, auth, butchering, catalog, corrections, documents, production, recalls,
                        reports, sales)

MODULES = [auth, catalog, production, butchering, alerts, sales, recalls, ai, reports, corrections, documents, admin]

router = APIRouter()
for _m in MODULES:
    router.include_router(_m.router)
