"""REST API for AVATAR Model 1. Main backend calls these endpoints after forecast/production events."""
from __future__ import annotations

import json
import os
import secrets
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.costing import calculate_ekp
from src.db import ROOT, get_engine
from src.retraining_policy import MIN_INITIAL_RECORDS, RETRAIN_NEW_RECORDS_THRESHOLD
from src.retraining_queue import enqueue_if_due

load_dotenv(ROOT / ".env")
app = FastAPI(title="AVATAR Model 1 API", version="1.0.0", description="Üretim verimi ve EKP tahmin servisi")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("AVATAR_AI_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="AVATAR_AI_API_KEY ayarlanmamış; servis güvenli şekilde kapalı.")
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik API anahtarı.")


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    production_order_id: str = Field(min_length=1, max_length=80)
    recipe_variant: str = Field(default="default", min_length=1, max_length=100)
    meat_kg: float = Field(gt=0, le=100000)
    spice_kg: float = Field(ge=0, le=10000)
    casing_kg: float = Field(ge=0, le=10000)
    package_weight_kg: float = Field(default=1.0, gt=0, le=100)
    planned_material_cost_eur: float = Field(ge=0, le=100000000)
    planned_service_cost_eur: float = Field(ge=0, le=100000000)


class ActualProductionRecord(BaseModel):
    """Main backend may call this only after a completed order is verified and finalized."""
    model_config = ConfigDict(extra="forbid")
    production_order_id: str = Field(min_length=1, max_length=80)
    production_date: date
    recipe_variant: str = Field(default="default", min_length=1, max_length=100)
    meat_kg: float = Field(gt=0, le=100000)
    spice_kg: float = Field(ge=0, le=10000)
    casing_kg: float = Field(ge=0, le=10000)
    package_weight_kg: float = Field(default=1.0, gt=0, le=100)
    planned_material_cost_eur: float = Field(ge=0, le=100000000)
    planned_service_cost_eur: float = Field(ge=0, le=100000000)
    actual_package_count: int = Field(gt=0, le=10000000)
    actual_material_cost_eur: float = Field(ge=0, le=100000000)
    actual_service_cost_eur: float = Field(ge=0, le=100000000)


def _db_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Veritabanı işlemi başarısız. DATABASE_URL ve SQL migration'ı kontrol edin. Ayrıntı: {type(exc).__name__}")



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "avatar-model1-api"}


@app.get("/ai/model/status", dependencies=[Depends(require_api_key)])
def model_status() -> dict:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            state = conn.execute(text("SELECT * FROM ai_retraining_state WHERE singleton_id=1")).mappings().first()
            active = conn.execute(text("SELECT model_version, artifact_path, algorithm, trained_record_count, metrics_json, activated_at FROM ai_model_registry WHERE is_active=1 ORDER BY activated_at DESC LIMIT 1")).mappings().first()
            latest_job = conn.execute(text("SELECT job_id, status, trigger_reason, records_total, new_records_since_attempt, created_at, started_at, finished_at, error_message, metrics_json FROM ai_retraining_jobs ORDER BY job_id DESC LIMIT 1")).mappings().first()
            total = int(conn.execute(text("""
                SELECT COUNT(*) FROM ai_production_training_records
                WHERE production_status='completed' AND validation_status='validated' AND data_source='actual'
            """)).scalar_one())
        return {
            "eligible_actual_records": total,
            "initial_training_threshold": MIN_INITIAL_RECORDS,
            "retraining_after_new_records": RETRAIN_NEW_RECORDS_THRESHOLD,
            "active_model": dict(active) if active else None,
            "retraining_state": dict(state) if state else None,
            "latest_job": dict(latest_job) if latest_job else None,
        }
    except Exception as exc:
        raise _db_error(exc) from exc


@app.post("/ai/production-forecast", dependencies=[Depends(require_api_key)])
def production_forecast(request: ForecastRequest) -> dict:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            active = conn.execute(text("SELECT model_version, artifact_path FROM ai_model_registry WHERE is_active=1 ORDER BY activated_at DESC LIMIT 1")).mappings().first()
        if not active:
            raise HTTPException(status_code=503, detail="Henüz AVATAR gerçek üretim verileriyle doğrulanmış aktif model yok. En az 100 doğrulanmış gerçek üretim kaydı gerekir.")
        artifact = (ROOT / str(active["artifact_path"])).resolve()
        if ROOT not in artifact.parents or not artifact.is_file():
            raise HTTPException(status_code=503, detail="Aktif model dosyası bulunamadı veya geçersiz yol.")
        bundle = joblib.load(artifact)
        input_row = pd.DataFrame([{
            "meat_kg": request.meat_kg,
            "spice_kg": request.spice_kg,
            "casing_kg": request.casing_kg,
            "package_weight_kg": request.package_weight_kg,
            "planned_material_cost_eur": request.planned_material_cost_eur,
            "planned_service_cost_eur": request.planned_service_cost_eur,
            "recipe_variant": request.recipe_variant,
        }])[bundle["feature_columns"]]
        predicted_packages = max(0.0, float(bundle["model"].predict(input_row)[0]))
        if predicted_packages < 0.5:
            raise HTTPException(status_code=422, detail="Model tahmini paket sayısı maliyet hesabı için sıfıra çok yakın.")
        predicted_ekp = calculate_ekp(request.planned_material_cost_eur, request.planned_service_cost_eur, predicted_packages)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ai_production_predictions
                (production_order_id, model_version, input_snapshot, predicted_output_quantity, predicted_ekp_eur, predicted_at)
                VALUES (:order_id, :model_version, :input_snapshot, :predicted_qty, :predicted_ekp, UTC_TIMESTAMP(6))
            """), {
                "order_id": request.production_order_id,
                "model_version": active["model_version"],
                "input_snapshot": json.dumps(request.model_dump(), ensure_ascii=False),
                "predicted_qty": predicted_packages,
                "predicted_ekp": predicted_ekp,
            })
        return {
            "production_order_id": request.production_order_id,
            "model_version": active["model_version"],
            "predicted_package_count": round(predicted_packages, 2),
            "predicted_ekp_eur": round(predicted_ekp, 4),
            "currency": "EUR",
            "note": "Bu tahmin yalnızca doğrulandığı üretim alanı ve veri dağılımı için kullanılmalıdır.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _db_error(exc) from exc


@app.post("/ai/production-records", dependencies=[Depends(require_api_key)])
def record_actual_production(request: ActualProductionRecord) -> dict:
    """Persist one completed+validated real production order and check retraining threshold."""
    actual_ekp = calculate_ekp(request.actual_material_cost_eur, request.actual_service_cost_eur, request.actual_package_count)
    try:
        engine = get_engine()
        with engine.begin() as conn:
            inserted = conn.execute(text("""
                INSERT IGNORE INTO ai_production_training_records (
                    production_order_id, production_date, recipe_variant, meat_kg, spice_kg, casing_kg,
                    package_weight_kg, planned_material_cost_eur, planned_service_cost_eur,
                    actual_package_count, actual_material_cost_eur, actual_service_cost_eur, actual_ekp_eur,
                    production_status, validation_status, data_source, recorded_at
                ) VALUES (
                    :production_order_id, :production_date, :recipe_variant, :meat_kg, :spice_kg, :casing_kg,
                    :package_weight_kg, :planned_material_cost_eur, :planned_service_cost_eur,
                    :actual_package_count, :actual_material_cost_eur, :actual_service_cost_eur, :actual_ekp_eur,
                    'completed', 'validated', 'actual', UTC_TIMESTAMP(6)
                )
            """), {**request.model_dump(), "actual_ekp_eur": actual_ekp})
            if inserted.rowcount == 0:
                return {"saved": False, "duplicate": True, "production_order_id": request.production_order_id, "message": "Bu üretim emri daha önce kaydedilmiş; çift kayıt oluşturulmadı."}
            conn.execute(text("""
                UPDATE ai_production_predictions
                SET actual_package_count=:actual_packages,
                    actual_ekp_eur=:actual_ekp,
                    actual_recorded_at=UTC_TIMESTAMP(6)
                WHERE production_order_id=:order_id AND actual_package_count IS NULL
            """), {
                "actual_packages": request.actual_package_count,
                "actual_ekp": actual_ekp,
                "order_id": request.production_order_id,
            })
            # Fill error columns as actual - prediction using a DB-side expression.
            conn.execute(text("""
                UPDATE ai_production_predictions
                SET quantity_error=actual_package_count-predicted_output_quantity,
                    ekp_error_eur=actual_ekp_eur-predicted_ekp_eur
                WHERE production_order_id=:order_id AND actual_package_count IS NOT NULL
            """), {"order_id": request.production_order_id})
            queue_status = enqueue_if_due(conn)
        return {
            "saved": True,
            "production_order_id": request.production_order_id,
            "actual_ekp_eur": round(actual_ekp, 4),
            "eligible_actual_records": queue_status["eligible_actual_records"],
            "initial_training_threshold": queue_status["initial_training_threshold"],
            "retraining_after_new_records": queue_status["retraining_after_new_records"],
            "retraining_job_enqueued": queue_status["enqueued"],
            "new_records_since_last_attempt": queue_status["new_records_since_last_attempt"],
            "message": "Gerçek üretim kaydı saklandı; eşik karşılanırsa eğitim işi otomatik kuyruğa alındı.",
        }
    except HTTPException:
        raise
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        raise _db_error(exc) from exc
    except Exception as exc:
        raise _db_error(exc) from exc
