import json
import hashlib

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.dummy import DummyRegressor

import app.main as main
from app.main import app
from Model2.training.train_model_b import FEATURES, TARGETS

client = TestClient(app)


def _write_test_model_bundle(tmp_path, estimator, *, source_type="measured", production_ready=True,
                             model_version="measured-test-model-v1", data_version="field-test-v1",
                             include_hash=True, manifest_overrides=None):
    bundle_path = tmp_path / "model_b_production.joblib"
    bundle = {"model": estimator, "feature_columns": FEATURES, "target_columns": TARGETS,
              "model_version": model_version, "data_version": data_version,
              "source_type": source_type, "production_ready": production_ready}
    joblib.dump(bundle, bundle_path)
    manifest = {"model_version": model_version, "data_version": data_version,
                "source_type": source_type, "production_ready": production_ready,
                "feature_columns": FEATURES, "target_columns": TARGETS}
    if include_hash:
        manifest["artifact_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (tmp_path / "model_b_production.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_path, manifest


def test_configured_model2_candidate_directory_still_refuses_production_prediction(monkeypatch):
    from pathlib import Path

    model2_dir = Path(__file__).resolve().parents[2] / "Model2" / "models"
    assert (model2_dir / "model_b_synthetic_candidate.joblib").is_file()
    assert not (model2_dir / "model_b_production.joblib").exists()
    assert not (model2_dir / "model_b_production.manifest.json").exists()
    monkeypatch.setattr(main, "MODEL_B_DIR", model2_dir)
    status = client.get("/v1/models/status")
    assert status.status_code == 200 and status.json()["model_b_production_ready"] is False
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503


def test_model_b_routes_report_unavailable_without_promoted_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    status = client.get("/v1/models/status")
    assert status.status_code == 200 and status.json()["model_b_production_ready"] is False
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503 and "hazır değil" in response.json()["detail"]
    assert str(tmp_path) not in response.text


def test_model_b_prediction_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "temporary-test-key")
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 401


def test_model_b_prediction_rejects_invalid_inputs():
    good = {"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2}
    assert client.post("/v1/predict/carcass-cuts", json=dict(good, extra=1)).status_code == 422
    assert client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "deve", "karkas_agirligi_kg": 18.2}).status_code == 422
    assert client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "dana", "karkas_agirligi_kg": -1}).status_code == 422
    assert client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu"}).status_code == 422
    assert client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": "heavy"}).status_code == 422
    for value in ("NaN", "Infinity", "-Infinity"):
        raw = '{"hayvan_turu":"kuzu","karkas_agirligi_kg":' + value + '}'
        assert client.post("/v1/predict/carcass-cuts", content=raw, headers={"content-type": "application/json"}).status_code == 422


def test_model_b_prediction_loads_measured_ready_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    train_x = pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}])
    train_y = pd.DataFrame([[1.0] * len(TARGETS)], columns=TARGETS)
    estimator.fit(train_x, train_y)
    _write_test_model_bundle(tmp_path, estimator)
    status = client.get("/v1/models/status").json()
    assert status["model_b_production_ready"] is True
    assert status["model_b_model_version"] == "measured-test-model-v1"
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data["predicted_cuts_kg"]) == set(TARGETS)
    assert data["model_version"] == "measured-test-model-v1" and data["source_type"] == "measured"


def test_model_b_evaluation_requires_configured_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "temporary-test-key")
    payload = {"predicted_cuts_kg": {target: 1.0 for target in TARGETS},
               "actual_cuts_kg": {target: 2.0 for target in TARGETS}}
    assert client.post("/v1/actual/carcass-cuts", json={"prediction_id":"00000000-0000-0000-0000-000000000000", "measured_at_utc":"2026-10-24T08:00:00+00:00", "actual_cuts_kg":payload["actual_cuts_kg"]}).status_code == 401


def test_model_b_prediction_does_not_serve_synthetic_candidate_even_if_misnamed(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    estimator.fit(pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}]), [[1.0] * len(TARGETS)])
    joblib.dump({"model": estimator, "feature_columns": FEATURES, "target_columns": TARGETS,
                 "model_version": "synthetic", "data_version": "synthetic", "source_type": "synthetic",
                 "production_ready": True}, tmp_path / "model_b_production.joblib")
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503


def test_model_b_hash_mismatch_is_rejected_before_joblib_load(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    artifact = tmp_path / "model_b_production.joblib"
    artifact.write_bytes(b"test artifact bytes")
    (tmp_path / "model_b_production.manifest.json").write_text(json.dumps({
        "model_version": "measured-v1", "data_version": "field-v1",
        "source_type": "measured", "production_ready": True,
        "feature_columns": FEATURES, "target_columns": TARGETS,
        "artifact_sha256": "0" * 64,
    }), encoding="utf-8")
    monkeypatch.setattr(main.joblib, "load", lambda *_: pytest.fail("joblib.load must not run before hash validation"))
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503
    assert client.get("/v1/models/status").json()["model_b_production_ready"] is False


def test_model_b_missing_manifest_hash_is_rejected_before_joblib_load(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    artifact = tmp_path / "model_b_production.joblib"
    artifact.write_bytes(b"test artifact bytes")
    (tmp_path / "model_b_production.manifest.json").write_text(json.dumps({
        "model_version": "measured-v1", "data_version": "field-v1",
        "source_type": "measured", "production_ready": True,
        "feature_columns": FEATURES, "target_columns": TARGETS,
    }), encoding="utf-8")
    monkeypatch.setattr(main.joblib, "load", lambda *_: pytest.fail("joblib.load must not run without a manifest hash"))
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503
    assert client.get("/v1/models/status").json()["model_b_production_ready"] is False


def test_model_b_production_artifact_without_manifest_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    (tmp_path / "model_b_production.joblib").write_bytes(b"unverified bytes")
    monkeypatch.setattr(main.joblib, "load", lambda *_: pytest.fail("joblib.load must not run without a manifest"))
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503
    assert client.get("/v1/models/status").json()["model_b_production_ready"] is False


def test_model_b_manifest_without_artifact_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    manifest = {"manifest_version": 1, "model_version": "measured-v1", "data_version": "field-v1",
                "source_type": "measured", "production_ready": True,
                "feature_columns": FEATURES, "target_columns": TARGETS,
                "artifact_sha256": "a" * 64}
    (tmp_path / "model_b_production.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503
    assert client.get("/v1/models/status").json()["model_b_production_ready"] is False


def test_model_b_manifest_bundle_version_mismatch_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    estimator.fit(pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}]), [[1.0] * len(TARGETS)])
    _write_test_model_bundle(tmp_path, estimator, manifest_overrides={"model_version": "other-version"})
    assert main._load_model_b_production_bundle() is None


def test_model_b_synthetic_manifest_rejected_before_joblib_load(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    estimator.fit(pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}]), [[1.0] * len(TARGETS)])
    _write_test_model_bundle(tmp_path, estimator, source_type="synthetic", production_ready=False)
    monkeypatch.setattr(main.joblib, "load", lambda *_: pytest.fail("synthetic bundle must be rejected before joblib.load"))
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503


def test_model_b_actual_endpoint_rejects_numeric_strings():
    payload = {"predicted_cuts_kg": {target: 1.0 for target in TARGETS},
               "actual_cuts_kg": {target: 2.0 for target in TARGETS}}
    payload["actual_cuts_kg"]["but_kg"] = "2.0"
    assert client.post("/v1/actual/carcass-cuts", json={"prediction_id":"00000000-0000-0000-0000-000000000000", "measured_at_utc":"2026-10-24T08:00:00+00:00", "actual_cuts_kg":payload["actual_cuts_kg"]}).status_code == 422

def test_model_b_persisted_prediction_then_measured_actual_then_evaluation(monkeypatch, tmp_path):
    import sqlite3
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    estimator.fit(pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}]), [[1.0] * len(TARGETS)])
    _write_test_model_bundle(tmp_path, estimator)

    prediction = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert prediction.status_code == 200
    prediction_id = prediction.json()["prediction_id"]
    assert prediction.json()["prediction_created_at_utc"].endswith("+00:00")
    assert client.get(f"/v1/evaluate/carcass-cuts/{prediction_id}").status_code == 409

    actual_payload = {"prediction_id": prediction_id, "measured_at_utc": "2026-10-24T08:00:00+03:00",
                      "actual_cuts_kg": {target: 2.0 for target in TARGETS}}
    actual = client.post("/v1/actual/carcass-cuts", json=actual_payload)
    assert actual.status_code == 200, actual.text
    assert actual.json()["actual_source_type"] == "measured"
    assert actual.json()["measured_at_utc"] == "2026-10-24T05:00:00+00:00"
    assert client.post("/v1/actual/carcass-cuts", json=actual_payload).status_code == 409

    evaluation = client.get(f"/v1/evaluate/carcass-cuts/{prediction_id}")
    assert evaluation.status_code == 200, evaluation.text
    result = evaluation.json()
    assert result["model_version"] == "measured-test-model-v1"
    assert result["actual_measured_at_utc"] == "2026-10-24T05:00:00+00:00"
    assert result["comparison"]["but_kg"]["deviation_kg"] == -1.0
    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        assert connection.execute("select count(*) from model_b_predictions").fetchone()[0] == 1
        assert connection.execute("select count(*) from model_b_actuals").fetchone()[0] == 1


def test_model_b_actual_endpoint_rejects_unknown_id_and_ambiguous_timestamp(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", tmp_path / "audit.sqlite3")
    valid_targets = {target: 2.0 for target in TARGETS}
    unknown = {"prediction_id": "00000000-0000-0000-0000-000000000000",
               "measured_at_utc": "2026-10-24T08:00:00+00:00", "actual_cuts_kg": valid_targets}
    assert client.post("/v1/actual/carcass-cuts", json=unknown).status_code == 404
    no_timezone = {**unknown, "measured_at_utc": "2026-10-24T08:00:00"}
    assert client.post("/v1/actual/carcass-cuts", json=no_timezone).status_code == 422

def test_stored_model_b_evaluation_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "temporary-test-key")
    assert client.get("/v1/evaluate/carcass-cuts/00000000-0000-0000-0000-000000000000").status_code == 401


def test_model_b_status_and_prediction_reject_corrupt_production_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    (tmp_path / "model_b_production.joblib").write_bytes(b"invalid artifact")
    status = client.get("/v1/models/status")
    assert status.status_code == 200 and status.json()["model_b_production_ready"] is False
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "dana", "karkas_agirligi_kg": 200.0})
    assert response.status_code == 503 and str(tmp_path) not in response.text

def test_model_b_prediction_fails_safely_when_audit_database_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "MODEL_B_DIR", tmp_path)
    broken_db = tmp_path / "db-path-is-a-directory"
    broken_db.mkdir()
    monkeypatch.setattr(main, "MODEL_B_AUDIT_DB", broken_db)
    estimator = DummyRegressor(strategy="constant", constant=np.array([1.0] * len(TARGETS)))
    estimator.fit(pd.DataFrame([{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 20.0}]), [[1.0] * len(TARGETS)])
    bundle_path = tmp_path / "model_b_production.joblib"
    _write_test_model_bundle(tmp_path, estimator, model_version="audit-failure-test-v1")
    response = client.post("/v1/predict/carcass-cuts", json={"hayvan_turu": "kuzu", "karkas_agirligi_kg": 18.2})
    assert response.status_code == 503
    assert "kayıt deposu" in response.json()["detail"]
    assert str(tmp_path) not in response.text

def test_model_b_actual_measurements_reject_negative_and_nonfinite_weights():
    valid = {"prediction_id": "00000000-0000-0000-0000-000000000001",
             "measured_at_utc": "2026-10-24T08:00:00+00:00",
             "actual_cuts_kg": {target: 2.0 for target in TARGETS}}
    negative = {**valid, "actual_cuts_kg": {**valid["actual_cuts_kg"], "but_kg": -1.0}}
    assert client.post("/v1/actual/carcass-cuts", json=negative).status_code == 422
    for literal in ("NaN", "Infinity", "-Infinity"):
        raw = json.dumps(valid, allow_nan=True).replace('"but_kg": 2.0', '"but_kg": ' + literal)
        response = client.post("/v1/actual/carcass-cuts", content=raw, headers={"content-type": "application/json"})
        assert response.status_code == 422
