from __future__ import annotations

import secrets
import sqlite3
from datetime import timezone

import numpy as np
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import API_KEY, APP_ENV, MODEL_B_AUDIT_DB, MODEL_B_DIR
from app.model_b_artifact import (
    load_production_bundle,
    read_production_manifest,
    read_synthetic_candidate_manifest,
)
from app.model_b_audit import (
    ActualAlreadyExists,
    ActualNotFound,
    PredictionNotFound,
    get_evaluation,
    save_actual,
    save_prediction,
)
from app.schemas import (
    MODEL_B_FEATURES,
    MODEL_B_TARGETS,
    CarcassCutsActualRequest,
    CarcassCutsActualResponse,
    CarcassCutsPredictionRequest,
    CarcassCutsPredictionResponse,
    Model2StatusResponse,
    StoredCarcassCutsEvaluationResponse,
)


MODEL_NOTICE = (
    "Saha doğrulamalı measured üretim artefaktı mevcut değil. "
    "Sentetik aday tahmin için yüklenmez."
)

app = FastAPI(
    title="AVATAR Model 2 Carcass Cuts API",
    version="1.0.0",
    description="Hayvan türü ve karkas ağırlığından karkas parçalarının tahmini.",
)


@app.exception_handler(RequestValidationError)
async def validation_error_response(_request, exc: RequestValidationError):
    errors = [
        {key: value for key, value in error.items() if key not in {"input", "ctx"}}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


def _authorize(x_api_key: str | None) -> None:
    if not API_KEY:
        if APP_ENV not in {"development", "dev", "test"}:
            raise HTTPException(
                status_code=503,
                detail="API kimlik doğrulaması yapılandırılmamış.",
            )
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik API anahtarı.")


@app.get("/health")
def health():
    """Liveness endpoint; model readiness is reported separately."""
    return {"status": "ok", "service": "avatar-model2-api"}


@app.get("/v1/models/status", response_model=Model2StatusResponse)
def model_status():
    production = read_production_manifest(MODEL_B_DIR)
    candidate = read_synthetic_candidate_manifest(MODEL_B_DIR)
    return Model2StatusResponse(
        service="avatar-model2-api",
        model_b_production_ready=production is not None,
        model_b_model_version=production.get("model_version") if production else None,
        model_b_data_version=production.get("data_version") if production else None,
        model_b_source_type=production.get("source_type") if production else None,
        model_b_candidate_available=candidate is not None,
        model_b_candidate_model_version=candidate.get("model_version") if candidate else None,
        model_b_candidate_data_version=candidate.get("data_version") if candidate else None,
        model_b_candidate_source_type=candidate.get("source_type") if candidate else None,
        model_b_candidate_production_ready=candidate.get("production_ready") if candidate else None,
        model_b_feature_columns=list(MODEL_B_FEATURES),
        model_b_target_columns=list(MODEL_B_TARGETS),
        model_notice=MODEL_NOTICE,
    )


@app.post("/v1/predict/carcass-cuts", response_model=CarcassCutsPredictionResponse)
def predict_carcass_cuts(
    payload: CarcassCutsPredictionRequest,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    bundle = load_production_bundle(MODEL_B_DIR)
    if bundle is None:
        raise HTTPException(
            status_code=503,
            detail="Model B saha doğrulamalı üretim artefaktı kullanıma hazır değil.",
        )

    try:
        frame = pd.DataFrame([payload.model_dump()], columns=bundle["feature_columns"])
        raw = np.asarray(bundle["model"].predict(frame), dtype=float)
        if raw.ndim == 2 and raw.shape[0] == 1:
            raw = raw[0]
        if raw.ndim != 1 or raw.shape[0] != len(MODEL_B_TARGETS) or not np.isfinite(raw).all():
            raise ValueError("invalid prediction shape or values")

        prediction = {
            target: round(max(0.0, float(value)), 3)
            for target, value in zip(MODEL_B_TARGETS, raw, strict=True)
        }
        prediction_id, created_at = save_prediction(
            MODEL_B_AUDIT_DB,
            bundle=bundle,
            species=payload.hayvan_turu,
            carcass_kg=payload.karkas_agirligi_kg,
            predicted_cuts=prediction,
        )
        return CarcassCutsPredictionResponse(
            predicted_cuts_kg=prediction,
            prediction_id=prediction_id,
            prediction_created_at_utc=created_at,
            model_version=bundle["model_version"],
            data_version=bundle["data_version"],
            source_type=bundle["source_type"],
            production_ready=True,
            model_notice="Model sürümü ve veri sürümü yanıtla döndürülür. Sonuçlar ölçüm ve kesim standardına bağlıdır.",
        )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Model B audit kayıt deposu kullanılamıyor.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model B artefaktı yüklenemedi veya şeması geçersiz.") from exc


@app.post("/v1/actual/carcass-cuts", response_model=CarcassCutsActualResponse)
def record_carcass_cuts_actual(
    payload: CarcassCutsActualRequest,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    if set(payload.actual_cuts_kg) != set(MODEL_B_TARGETS):
        raise HTTPException(status_code=422, detail="Gerçek ölçümler tüm tanımlı hedefleri içermelidir.")
    try:
        measured_at = payload.measured_at_utc.astimezone(timezone.utc).isoformat()
        recorded_at = save_actual(
            MODEL_B_AUDIT_DB,
            payload.prediction_id,
            payload.actual_cuts_kg,
            measured_at,
        )
    except PredictionNotFound:
        raise HTTPException(status_code=404, detail="Tahmin kaydı bulunamadı.")
    except ActualAlreadyExists:
        raise HTTPException(status_code=409, detail="Bu tahmin için gerçekleşen ölçüm zaten kaydedilmiş.")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Model B audit kayıt deposu kullanılamıyor.") from exc
    return CarcassCutsActualResponse(
        prediction_id=payload.prediction_id,
        recorded_at_utc=recorded_at,
        measured_at_utc=measured_at,
        actual_source_type="measured",
    )


@app.get("/v1/evaluate/carcass-cuts/{prediction_id}", response_model=StoredCarcassCutsEvaluationResponse)
def evaluate_stored_carcass_cuts(
    prediction_id: str,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    try:
        result = get_evaluation(MODEL_B_AUDIT_DB, prediction_id)
    except PredictionNotFound:
        raise HTTPException(status_code=404, detail="Tahmin kaydı bulunamadı.")
    except ActualNotFound:
        raise HTTPException(status_code=409, detail="Gerçek ölçüm henüz kaydedilmedi.")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Model B audit kayıt deposu kullanılamıyor.") from exc
    result["deviation_convention"] = (
        "Fark = tahmin - gerçekleşen; pozitif değer fazla tahmini, negatif değer düşük tahmini gösterir."
    )
    return result
