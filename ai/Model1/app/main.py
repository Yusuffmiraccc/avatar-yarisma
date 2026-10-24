from pathlib import Path
from datetime import timezone
import math
import hashlib
import joblib
import json
import secrets
import sqlite3
import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.config import MODEL_DIR, MODEL_B_DIR, MODEL_B_AUDIT_DB, API_KEY, APP_ENV
from app.schemas import (
    ProductionPredictionRequest, ProductionPredictionResponse,
    CarcassCutsPredictionRequest, CarcassCutsPredictionResponse,
    CarcassCutsActualRequest, CarcassCutsActualResponse, StoredCarcassCutsEvaluationResponse,
    MODEL_B_TARGETS,
)
from app.model_b_audit import (
    ActualAlreadyExists, ActualNotFound, PredictionNotFound,
    get_evaluation as get_model_b_evaluation,
    save_actual as save_model_b_actual,
    save_prediction as save_model_b_prediction,
)

app = FastAPI(
    title="AVATAR Production ML API",
    version="0.1.0",
    description="Sucuk üretim verimi ve EKP tahmini. Tahminler karar destek amaçlıdır."
)


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, exc: RequestValidationError):
    # Error inputs can contain NaN/Infinity, which are not valid JSON response values.
    errors = [{key: value for key, value in error.items() if key not in {"input", "ctx"}}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})

MODEL_FEATURES_A = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg", "Kilif_metre", "Et_fiyat_TL_kg", "Kuyruk_yagi_fiyat_TL_kg",
    "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg", "Kilif_fiyat_TL_m",
    "Fason_birim_bedel_TL_kg_girdi", "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun", "Bolge", "Recete_profili", "Isleme_modeli",
]

def _load_model(filename):
    path = MODEL_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=503, detail="API modeli kullanıma hazır değil; model dosyası kurulu değil.")
    try:
        loaded = joblib.load(path)
    except Exception as exc:
        # Do not expose local paths, serialization details, or stack traces to clients.
        raise HTTPException(status_code=503, detail="Model dosyası yüklenemedi; servis yöneticisi model kurulumunu kontrol etmelidir.") from exc
    return loaded if isinstance(loaded, dict) else {"model": loaded}


def _predict(model_bundle, request_values):
    model = model_bundle["model"]
    features = model_bundle.get("feature_columns") or list(getattr(model, "feature_names_in_", MODEL_FEATURES_A))
    row = pd.DataFrame([{name: request_values.get(name) for name in features}], columns=features)
    return float(model.predict(row)[0])


def _sha256_fileobj(file_obj):
    digest = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _load_model_b_production_bundle():
    """Load only an explicitly promoted, measured Model B artifact."""
    path = MODEL_B_DIR / "model_b_production.joblib"
    manifest = _read_model_b_manifest()
    if not path.is_file() or manifest is None:
        return None
    try:
        # Hash and deserialize through the same open file handle. This verifies
        # the exact bytes handed to joblib, before any pickle code is loaded.
        with path.open("rb") as artifact_file:
            artifact_sha256 = _sha256_fileobj(artifact_file)
            if not secrets.compare_digest(artifact_sha256, manifest["artifact_sha256"].lower()):
                return None
            artifact_file.seek(0)
            bundle = joblib.load(artifact_file)
        expected_features = ["hayvan_turu", "karkas_agirligi_kg"]
        if (
            not isinstance(bundle, dict)
            or bundle.get("production_ready") is not True
            or bundle.get("source_type") != "measured"
            or bundle.get("feature_columns") != expected_features
            or bundle.get("target_columns") != list(MODEL_B_TARGETS)
            or not bundle.get("model_version")
            or not bundle.get("data_version")
            or not hasattr(bundle.get("model"), "predict")
            or bundle.get("model_version") != manifest["model_version"]
            or bundle.get("data_version") != manifest["data_version"]
        ):
            return None
        return bundle
    except Exception:
        return None


def _read_model_b_manifest():
    """Read public status metadata without unpickling a model on an unauthenticated GET."""
    manifest_path = MODEL_B_DIR / "model_b_production.manifest.json"
    if not (MODEL_B_DIR / "model_b_production.joblib").is_file() or not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hash = manifest.get("artifact_sha256")
        if (
            manifest.get("production_ready") is not True
            or manifest.get("source_type") != "measured"
            or manifest.get("feature_columns") != ["hayvan_turu", "karkas_agirligi_kg"]
            or manifest.get("target_columns") != list(MODEL_B_TARGETS)
            or not manifest.get("model_version")
            or not manifest.get("data_version")
            or not _valid_sha256(expected_hash)
        ):
            return None
        with (MODEL_B_DIR / "model_b_production.joblib").open("rb") as artifact_file:
            actual_hash = _sha256_fileobj(artifact_file)
        if not secrets.compare_digest(actual_hash, expected_hash.lower()):
            return None
        return manifest
    except (OSError, json.JSONDecodeError, AttributeError):
        return None

def _authorize(x_api_key):
    if not API_KEY:
        if APP_ENV not in {"development", "dev", "test"}:
            raise HTTPException(status_code=503, detail="API kimlik doğrulaması yapılandırılmamış.")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik API anahtarı.")

@app.get("/health")
def health():
    return {"status": "ok", "service": "avatar-production-ml-api"}

@app.get("/v1/models/status")
def model_status():
    metrics_path = MODEL_DIR.parent / "reports" / "model_comparison.json"
    ekp_ready = False
    if metrics_path.exists():
        try:
            validation = json.loads(metrics_path.read_text(encoding="utf-8"))
            ekp_ready = validation.get("production_readiness", {}).get("ekp") == "READY"
        except (OSError, json.JSONDecodeError):
            ekp_ready = False
    model_b_manifest = _read_model_b_manifest()
    return {
        "yield_model_trained": (MODEL_DIR / "yield_model.joblib").exists(),
        "ekp_model_trained": (MODEL_DIR / "ekp_model.joblib").exists(),
        "lamb_cutting_model": "production_artifact_available" if model_b_manifest else "not_available",
        "model_b_production_ready": model_b_manifest is not None,
        "model_b_model_version": model_b_manifest.get("model_version") if model_b_manifest else None,
        "model_b_data_version": model_b_manifest.get("data_version") if model_b_manifest else None,
        "ekp_production_ready": ekp_ready,
        "ekp_warning": "EKP modeli baseline ve sentetik veri doğrulaması nedeniyle üretim kullanımı için hazır kabul edilmemelidir.",
        "model_scenario": "Scenario A; only allow-listed production-before features are used. Optional loss rates are planning assumptions and are ignored by this endpoint; no Scenario B model is deployed.",
        "note": "Sentetik Model B adayı ayrı saklanır; yalnızca model_b_production.joblib adıyla konmuş artefakt API'de kullanılabilir."
    }

@app.post("/v1/predict/production", response_model=ProductionPredictionResponse)
def predict_production(payload: ProductionPredictionRequest, x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    yield_model = _load_model("yield_model.joblib")
    ekp_model = _load_model("ekp_model.joblib")
    request_values = payload.model_dump(exclude_none=True)
    predicted_yield = _predict(yield_model, request_values)
    predicted_ekp = _predict(ekp_model, request_values)
    input_mass_kg = sum(request_values[name] for name in (
        "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg",
        "Tuz_girdi_kg", "Diger_kucuk_girdi_kg",
    ))
    if (
        not math.isfinite(predicted_yield)
        or predicted_yield < 0
        or predicted_yield > input_mass_kg + 0.01
        or not math.isfinite(predicted_ekp)
        or predicted_ekp < 0
    ):
        raise HTTPException(status_code=503, detail="Model fiziksel olarak geçersiz bir tahmin üretti.")
    return ProductionPredictionResponse(
        predicted_net_output_kg=round(predicted_yield, 3),
        predicted_ekp_tl_per_kg=round(predicted_ekp, 2),
        model_notice="EKP modeli üretim kullanımı için hazır değildir. Eğitim verisi sentetik/simüledir; tahminler dış doğrulama olmadan karar veya muhasebe kaydı için kullanılmamalıdır. Bu Scenario A endpoint'i opsiyonel kuruma/ayıklama alanlarını kullanmaz; Scenario B için bu alanlar ancak üretim öncesi planlama varsayımı olarak doğrulanırsa kullanılabilir. Gerçekleşmiş ölçümleri tahmin girdisi olarak göndermeyin."
    )

@app.get("/")
def root():
    return {"message": "AVATAR ML API çalışıyor.", "docs": "/docs", "health": "/health"}

from app.schemas import ProductionEvaluationRequest, ProductionEvaluationResponse


@app.post(
    "/v1/evaluate/production",
    response_model=ProductionEvaluationResponse,
)
def evaluate_production(
    payload: ProductionEvaluationRequest,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    predicted_yield = round(payload.predicted_net_output_kg, 3)
    actual_yield = round(payload.actual_net_output_kg, 3)

    predicted_ekp = round(payload.predicted_ekp_tl_per_kg, 2)
    actual_ekp = round(
        payload.actual_total_cost_tl / payload.actual_net_output_kg,
        2,
    )

    return ProductionEvaluationResponse(
        predicted_net_output_kg=predicted_yield,
        actual_net_output_kg=actual_yield,
        yield_deviation_kg=round(predicted_yield - actual_yield, 3),
        predicted_ekp_tl_per_kg=predicted_ekp,
        actual_total_cost_tl=round(payload.actual_total_cost_tl, 2),
        actual_ekp_tl_per_kg=actual_ekp,
        ekp_deviation_tl_per_kg=round(predicted_ekp - actual_ekp, 2),
        deviation_convention="Fark = tahmin - gerçekleşen; pozitif değer fazla tahmini, negatif değer düşük tahmini gösterir.",
    )


@app.post("/v1/predict/carcass-cuts", response_model=CarcassCutsPredictionResponse)
def predict_carcass_cuts(
    payload: CarcassCutsPredictionRequest,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    bundle = _load_model_b_production_bundle()
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model B saha doğrulamalı üretim artefaktı kullanıma hazır değil.")
    try:
        model = bundle["model"]
        features = bundle["feature_columns"]
        targets = bundle["target_columns"]
        row = pd.DataFrame([payload.model_dump()], columns=features)
        raw_prediction = model.predict(row)[0]
        prediction = {target: round(max(0.0, float(value)), 3) for target, value in zip(targets, raw_prediction)}
        if set(prediction) != set(MODEL_B_TARGETS):
            raise ValueError("target schema mismatch")
        prediction_id, created_at = save_model_b_prediction(
            MODEL_B_AUDIT_DB, bundle=bundle, species=payload.hayvan_turu,
            carcass_kg=payload.karkas_agirligi_kg, predicted_cuts=prediction,
        )
        return CarcassCutsPredictionResponse(
            predicted_cuts_kg=prediction,
            prediction_id=prediction_id,
            prediction_created_at_utc=created_at,
            model_version=str(bundle["model_version"]),
            data_version=str(bundle["data_version"]),
            source_type=str(bundle.get("source_type", "unknown")),
            production_ready=True,
            model_notice="Model sürümü ve veri sürümü yanıtla döndürülür. Sonuçlar ölçüm ve kesim standardına bağlıdır.",
        )
    except HTTPException:
        raise
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Model B audit kayıt deposu kullanılamıyor.") from exc
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
        recorded_at = save_model_b_actual(
            MODEL_B_AUDIT_DB, payload.prediction_id, payload.actual_cuts_kg,
            payload.measured_at_utc.astimezone(timezone.utc).isoformat(),
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
        measured_at_utc=payload.measured_at_utc.astimezone(timezone.utc).isoformat(),
        actual_source_type="measured",
    )


@app.get("/v1/evaluate/carcass-cuts/{prediction_id}", response_model=StoredCarcassCutsEvaluationResponse)
def evaluate_stored_carcass_cuts(
    prediction_id: str,
    x_api_key: str | None = Header(default=None),
):
    _authorize(x_api_key)
    try:
        result = get_model_b_evaluation(MODEL_B_AUDIT_DB, prediction_id)
    except PredictionNotFound:
        raise HTTPException(status_code=404, detail="Tahmin kaydı bulunamadı.")
    except ActualNotFound:
        raise HTTPException(status_code=409, detail="Gerçek ölçüm henüz kaydedilmedi.")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Model B audit kayıt deposu kullanılamıyor.") from exc
    result["deviation_convention"] = "Fark = tahmin - gerçekleşen; pozitif değer fazla tahmini, negatif değer düşük tahmini gösterir."
    return result


