from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import bad_request, not_found
from app.ml import service as ml
from app.ml import synthetic
from app.models import ButcheringOrder, MlPrediction, ProductionOrder
from app.schemas.common import ApiModel, Dec, Page, PageParams, paginate, redact_cost_data

router = APIRouter(prefix="/ai", tags=["ai"])
PP = Annotated[PageParams, Depends()]


class PredictionOut(ApiModel):
    id: int
    prediction_type: str
    model_version: str
    status: str
    input_reference_type: str | None = None
    input_reference_id: int | None = None
    input_summary: dict | None = None
    predicted_value: Dec | None = None
    predicted_cost: Dec | None = None
    baseline_value: Dec | None = None
    baseline_cost: Dec | None = None
    actual_value: Dec | None = None
    actual_cost: Dec | None = None
    metric_name: str | None = None
    error_value: Dec | None = None
    detail: dict | None = None
    limitations_note: str | None = None
    created_at: datetime


class ProductionPredictIn(BaseModel):
    production_order_id: int


class ButcheringPredictIn(BaseModel):
    butchering_order_id: int | None = None
    animal_type: str | None = Field(default=None, max_length=40)
    input_weight: Dec | None = None


class SyntheticIn(BaseModel):
    production_orders: int = Field(default=120, ge=0, le=1000)
    butchering_orders: int = Field(default=150, ge=0, le=1000)


def _respond(pred: MlPrediction, user):
    out = PredictionOut.model_validate(pred)
    content = jsonable_encoder(out)
    if pred.status == "FAILED":
        content["detail"] = {"message": "Tahmin üretilemedi."}
    if "costs:read" not in user.permissions:
        content = redact_cost_data(content)
    if pred.status == "FAILED":  # ML arızası yalnızca bu uç noktayı etkiler; operasyon akışları çalışır
        return JSONResponse(status_code=503, content={"error": {"code": "MODEL_NOT_AVAILABLE",
                            "message": "Tahmin üretilemedi."}, "prediction": content})
    return JSONResponse(content=content)


@router.post("/synthetic-data")
def synthetic_data(body: SyntheticIn, db: DB, _=require("ai:run")):
    """DEMO: sentetik geçmiş üretim/parçalama verisi üretir (is_demo=True). Gerçek veri değildir."""
    return {"production_orders_created": synthetic.generate_production(db, body.production_orders),
            "butchering_orders_created": synthetic.generate_butchering(db, body.butchering_orders),
            "note": "Sentetik DEMO verisi; gerçek üretici verisi değildir."}


@router.post("/models/train")
def train(db: DB, _=require("ai:run")):
    return ml.train_all(db)


@router.get("/models")
def models(_=require("ai:read")):
    return {k: ml.summary(ml.artifact(k)) for k in ml.KIND_FILE}


@router.post("/production-yield/predict", response_model=PredictionOut)
def predict_production(body: ProductionPredictIn, db: DB, user=require("ai:run")):
    order = db.get(ProductionOrder, body.production_order_id)
    if order is None:
        raise not_found("Üretim emri", body.production_order_id)
    return _respond(ml.predict_production(db, order, user.id), user)


@router.post("/butchering-output/predict", response_model=PredictionOut)
def predict_butchering(body: ButcheringPredictIn, db: DB, user=require("ai:run")):
    order = None
    if body.butchering_order_id is not None:
        order = db.get(ButcheringOrder, body.butchering_order_id)
        if order is None:
            raise not_found("Parçalama emri", body.butchering_order_id)
        animal, weight = order.animal_type, order.input_weight
    elif body.animal_type and body.input_weight:
        animal, weight = body.animal_type, body.input_weight
    else:
        raise bad_request("butchering_order_id veya animal_type + input_weight verilmelidir.")
    return _respond(ml.predict_butchering(db, animal, weight, order, user.id), user)


@router.get("/predictions", response_model=Page[PredictionOut])
def list_predictions(db: DB, p: PP, prediction_type: str | None = None, user=require("ai:read")):
    stmt = select(MlPrediction).order_by(MlPrediction.id.desc())
    if prediction_type:
        stmt = stmt.where(MlPrediction.prediction_type == prediction_type)
    res = paginate(db, stmt, p)
    for pr in res["items"]:
        ml.refresh_actual(db, pr)
    content = jsonable_encoder(res)
    for item, pr in zip(content["items"], res["items"], strict=True):
        if pr.status == "FAILED":
            item["detail"] = {"message": "Tahmin üretilemedi."}
    if "costs:read" not in user.permissions:
        content = redact_cost_data(content)
    return JSONResponse(content=content)


@router.get("/predictions/{prediction_id}", response_model=PredictionOut)
def get_prediction(prediction_id: int, db: DB, user=require("ai:read")):
    pr = db.get(MlPrediction, prediction_id)
    if pr is None:
        raise not_found("Tahmin", prediction_id)
    ml.refresh_actual(db, pr)
    content = jsonable_encoder(PredictionOut.model_validate(pr))
    if pr.status == "FAILED":
        content["detail"] = {"message": "Tahmin üretilemedi."}
    if "costs:read" not in user.permissions:
        content = redact_cost_data(content)
    return JSONResponse(content=content)
