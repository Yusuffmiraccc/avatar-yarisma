from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.model_b_artifact as artifact
from app.schemas import MODEL_B_FEATURES, MODEL_B_TARGETS


class FixedModel:
    def predict(self, frame):
        return np.tile(np.arange(1, len(MODEL_B_TARGETS) + 1, dtype=float), (len(frame), 1))


client = TestClient(main.app)


def _write_production_bundle(directory: Path, *, source_type="measured", production_ready=True, artifact_hash=None):
    directory.mkdir(parents=True, exist_ok=True)
    bundle_path = directory / artifact.PRODUCTION_FILENAME
    bundle = {
        "model": FixedModel(),
        "feature_columns": list(MODEL_B_FEATURES),
        "target_columns": list(MODEL_B_TARGETS),
        "model_version": "measured-test-v1",
        "data_version": "field-test-v1",
        "source_type": source_type,
        "production_ready": production_ready,
    }
    import joblib

    joblib.dump(bundle, bundle_path)
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    manifest = {
        "manifest_version": 1,
        "artifact_filename": artifact.PRODUCTION_FILENAME,
        "artifact_sha256": artifact_hash or digest,
        "model_version": bundle["model_version"],
        "data_version": bundle["data_version"],
        "source_type": source_type,
        "production_ready": production_ready,
        "feature_columns": list(MODEL_B_FEATURES),
        "target_columns": list(MODEL_B_TARGETS),
    }
    (directory / artifact.PRODUCTION_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_path


def _write_candidate_bundle(directory: Path, *, source_type="synthetic", production_ready=False, artifact_hash=None):
    directory.mkdir(parents=True, exist_ok=True)
    bundle_path = directory / artifact.CANDIDATE_FILENAME
    bundle = {
        "model": FixedModel(),
        "feature_columns": list(MODEL_B_FEATURES),
        "target_columns": list(MODEL_B_TARGETS),
        "model_version": "synthetic-candidate-v1",
        "data_version": "synthetic-data-v1",
        "source_type": source_type,
        "production_ready": production_ready,
    }
    import joblib

    joblib.dump(bundle, bundle_path)
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    manifest = {
        "manifest_version": 1,
        "artifact_filename": artifact.CANDIDATE_FILENAME,
        "artifact_sha256": artifact_hash or digest,
        "model_version": bundle["model_version"],
        "data_version": bundle["data_version"],
        "source_type": source_type,
        "production_ready": production_ready,
        "feature_columns": list(MODEL_B_FEATURES),
        "target_columns": list(MODEL_B_TARGETS),
    }
    (directory / artifact.CANDIDATE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_path


def test_health_and_status_are_model2_specific(monkeypatch):
    model_dir = Path(__file__).resolve().parents[1] / "models"
    monkeypatch.setattr(main, "MODEL_B_DIR", model_dir)
    monkeypatch.setattr(artifact.joblib, "load", lambda *_: pytest.fail("status must not unpickle models"))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "avatar-model2-api"}

    response = client.get("/v1/models/status")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "avatar-model2-api"
    assert body["model_b_production_ready"] is False
    assert body["model_b_model_version"] is None
    assert body["model_b_candidate_available"] is True
    assert body["model_b_candidate_source_type"] == "synthetic"
    assert body["model_b_candidate_production_ready"] is False
    assert body["model_b_feature_columns"] == list(MODEL_B_FEATURES)
    assert body["model_b_target_columns"] == list(MODEL_B_TARGETS)
    assert not {
        "yield_model_trained", "ekp_model_trained", "lamb_cutting_model", "ekp_production_ready"
    }.intersection(body)


def test_prediction_returns_503_without_measured_production_artifact(monkeypatch):
    monkeypatch.setattr(main, "MODEL_B_DIR", Path(__file__).resolve().parents[1] / "models")
    monkeypatch.setattr(main, "API_KEY", "test-key")
    response = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 503
    assert "üretim artefaktı" in response.json()["detail"]


def test_prediction_requires_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-key")
    response = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"hayvan_turu": "deve", "karkas_agirligi_kg": 18.2},
        {"hayvan_turu": "kuzu", "karkas_agirligi_kg": -1},
        {"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2, "extra": True},
        {"hayvan_turu": "kuzu"},
    ],
)
def test_prediction_request_rejects_invalid_input(payload, monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-key")
    response = client.post(
        "/v1/predict/carcass-cuts",
        json=payload,
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 422


def test_prediction_rejects_hash_mismatch_before_deserialization(tmp_path, monkeypatch):
    _write_production_bundle(tmp_path, artifact_hash="0" * 64)
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "API_KEY", "test-key")
    monkeypatch.setattr(artifact.joblib, "load", lambda *_: pytest.fail("invalid hash must be rejected first"))
    response = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 503


def test_synthetic_bundle_named_as_production_is_not_served(tmp_path, monkeypatch):
    _write_production_bundle(tmp_path, source_type="synthetic", production_ready=False)
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "API_KEY", "test-key")
    monkeypatch.setattr(artifact.joblib, "load", lambda *_: pytest.fail("synthetic artifact must not be loaded"))
    response = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 503


def test_measured_prediction_actual_and_evaluation_flow(tmp_path, monkeypatch):
    _write_production_bundle(tmp_path)
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    monkeypatch.setattr(main, "API_KEY", "test-key")
    headers = {"x-api-key": "test-key"}

    prediction = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers=headers,
    )
    assert prediction.status_code == 200
    prediction_body = prediction.json()
    assert set(prediction_body["predicted_cuts_kg"]) == set(MODEL_B_TARGETS)
    assert prediction_body["predicted_cuts_kg"] == {
        target: float(index) for index, target in enumerate(MODEL_B_TARGETS, start=1)
    }
    assert prediction_body["production_ready"] is True

    actual_body = {
        "prediction_id": prediction_body["prediction_id"],
        "measured_at_utc": "2026-01-01T08:00:00+00:00",
        "actual_cuts_kg": {target: float(index) for index, target in enumerate(MODEL_B_TARGETS, start=1)},
    }
    actual = client.post("/v1/actual/carcass-cuts", json=actual_body, headers=headers)
    assert actual.status_code == 200
    assert actual.json()["actual_source_type"] == "measured"

    evaluation = client.get(
        f"/v1/evaluate/carcass-cuts/{prediction_body['prediction_id']}",
        headers=headers,
    )
    assert evaluation.status_code == 200
    assert set(evaluation.json()["comparison"]) == set(MODEL_B_TARGETS)


def test_experimental_prediction_requires_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-key")
    response = client.post(
        "/v1/predict/carcass-cuts/experimental",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
    )
    assert response.status_code == 401


def test_production_endpoint_still_fails_closed_when_candidate_is_present(monkeypatch):
    real_model_dir = Path(__file__).resolve().parents[1] / "models"
    monkeypatch.setattr(main, "MODEL_B_DIR", real_model_dir)
    monkeypatch.setattr(main, "API_KEY", "test-key")
    headers = {"x-api-key": "test-key"}

    # Production endpoint must strictly fail closed (503)
    response = client.post(
        "/v1/predict/carcass-cuts",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0},
        headers=headers,
    )
    assert response.status_code == 503
    assert "üretim artefaktı" in response.json()["detail"]


def test_experimental_prediction_with_real_candidate_model(tmp_path, monkeypatch):
    real_model_dir = Path(__file__).resolve().parents[1] / "models"
    monkeypatch.setattr(main, "MODEL_B_DIR", real_model_dir)
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    monkeypatch.setattr(main, "API_KEY", "test-key")
    headers = {"x-api-key": "test-key"}

    response = client.post(
        "/v1/predict/carcass-cuts/experimental",
        json={"hayvan_turu": "dana", "karkas_agirligi_kg": 250.0},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["experimental"] is True
    assert body["production_ready"] is False
    assert body["source_type"] == "synthetic"
    assert set(body["predicted_cuts_kg"]) == set(MODEL_B_TARGETS)
    for cut, kg in body["predicted_cuts_kg"].items():
        assert isinstance(kg, (int, float))
        assert kg >= 0.0
    assert "DENEYSEL PİLOT TAHMİNİ" in body["model_notice"]


def test_experimental_prediction_rejects_hash_mismatch(tmp_path, monkeypatch):
    _write_candidate_bundle(tmp_path, artifact_hash="0" * 64)
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "API_KEY", "test-key")
    monkeypatch.setattr(artifact.joblib, "load", lambda *_: pytest.fail("invalid hash must be rejected first"))
    response = client.post(
        "/v1/predict/carcass-cuts/experimental",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 503


def test_experimental_prediction_returns_503_when_no_candidate(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.setattr(main, "MODEL_B_DIR", empty_dir)
    monkeypatch.setattr(main, "API_KEY", "test-key")
    response = client.post(
        "/v1/predict/carcass-cuts/experimental",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers={"x-api-key": "test-key"},
    )
    assert response.status_code == 503


def test_experimental_prediction_actual_and_evaluation_flow(tmp_path, monkeypatch):
    _write_candidate_bundle(tmp_path)
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    monkeypatch.setattr(main, "API_KEY", "test-key")
    headers = {"x-api-key": "test-key"}

    prediction = client.post(
        "/v1/predict/carcass-cuts/experimental",
        json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2},
        headers=headers,
    )
    assert prediction.status_code == 200
    prediction_body = prediction.json()
    assert prediction_body["experimental"] is True
    assert prediction_body["production_ready"] is False
    assert prediction_body["source_type"] == "synthetic"
    assert set(prediction_body["predicted_cuts_kg"]) == set(MODEL_B_TARGETS)

    actual_body = {
        "prediction_id": prediction_body["prediction_id"],
        "measured_at_utc": "2026-01-01T08:00:00+00:00",
        "actual_cuts_kg": {target: float(index) for index, target in enumerate(MODEL_B_TARGETS, start=1)},
    }
    actual = client.post("/v1/actual/carcass-cuts", json=actual_body, headers=headers)
    assert actual.status_code == 200
    assert actual.json()["actual_source_type"] == "measured"

    evaluation = client.get(
        f"/v1/evaluate/carcass-cuts/{prediction_body['prediction_id']}",
        headers=headers,
    )
    assert evaluation.status_code == 200
    eval_body = evaluation.json()
    assert eval_body["source_type"] == "synthetic"
    assert eval_body["is_experimental"] is True
    assert set(eval_body["comparison"]) == set(MODEL_B_TARGETS)
