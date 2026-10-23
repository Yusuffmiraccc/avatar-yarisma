import pytest

from app.core.config import get_settings
from tests.test_production import run_reference_order


@pytest.fixture(autouse=True)
def _ml_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "ml_dir", str(tmp_path / "ml"))
    from app.ml import service
    service._cache.clear()


def _train(client, h):
    assert client.post("/api/v1/ai/synthetic-data", headers=h, json={}).status_code == 200
    r = client.post("/api/v1/ai/models/train", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_prediction_without_model_fails_softly_and_ops_continue(client, auth):
    h = auth("ADMIN")
    oid, sucuk, _ = run_reference_order(client, h)
    r = client.post("/api/v1/ai/production-yield/predict", headers=h, json={"production_order_id": oid})
    assert r.status_code == 503 and r.json()["error"]["code"] == "MODEL_NOT_AVAILABLE"
    # ML arızası üretim tamamlamayı engellemez
    done = client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-1", "quantity": "85", "unit_code": "PACK"}]})
    assert done.status_code == 200


def test_prediction_exception_details_are_not_disclosed_or_persisted(client, auth, monkeypatch, caplog):
    import logging

    from app.ml import service as ml_service
    from tests.test_production import run_reference_order

    admin = auth("ADMIN")
    order_id, _, _ = run_reference_order(client, admin)
    secret_detail = "C:\\private\\models\\artifact.joblib INTERNAL_PICKLE_SENTINEL"
    monkeypatch.setattr(ml_service, "artifact", lambda _kind: {"version": "test-model"})

    def fail_prediction(*_args, **_kwargs):
        raise RuntimeError(secret_detail)

    monkeypatch.setattr(ml_service.modeling, "predict_production", fail_prediction)
    caplog.set_level(logging.ERROR, logger="app.ml.service")
    response = client.post("/api/v1/ai/production-yield/predict", headers=admin,
                           json={"production_order_id": order_id})
    assert response.status_code == 503
    assert "Tahmin üretilemedi." in response.text
    assert secret_detail not in response.text and "INTERNAL_PICKLE_SENTINEL" not in response.text
    prediction_id = response.json()["prediction"]["id"]
    assert secret_detail not in caplog.text and "INTERNAL_PICKLE_SENTINEL" not in caplog.text

    viewer = auth("VIEWER")
    history = client.get("/api/v1/ai/predictions", headers=viewer).json()
    detail = client.get(f"/api/v1/ai/predictions/{prediction_id}", headers=viewer).json()
    assert secret_detail not in str(history) and secret_detail not in str(detail)
    assert detail["detail"] == {"message": "Tahmin üretilemedi."}


def test_training_reports_baseline_comparison_and_beats_baseline(client, auth):
    h = auth("ADMIN")
    m = _train(client, h)
    a, b = m["production_yield"], m["butchering_output"]
    assert a["n_samples"] >= 100 and b["n_samples"] >= 100
    cv = a["metrics"]["cross_validation"]
    assert "BASELINE_MEAN" in cv["by_model"] and cv["selected_model"] in cv["by_model"]
    assert cv["improvement_over_baseline_percent"]["output_quantity_mae"] > 0
    assert a["metrics"]["temporal_holdout"]["n_test"] > 0
    assert a["limitations"] and "sentetik" in a["limitations"][0].lower()
    assert b["metrics"]["cross_validation"]["improvement_over_baseline_percent"]["overall_mae_kg"] > 0
    assert client.get("/api/v1/ai/models", headers=auth("VIEWER")).json()["production_yield"]["version"] == a["version"]


def test_production_prediction_vs_actual_deviation(client, auth):
    h = auth("ADMIN")
    oid, sucuk, _ = run_reference_order(client, h)  # 100/2/5 kg girdi, hizmet 5.50/paket
    _train(client, h)
    p = client.post("/api/v1/ai/production-yield/predict", headers=h, json={"production_order_id": oid})
    assert p.status_code == 200, p.text
    pj = p.json()
    assert pj["status"] == "SUCCEEDED" and pj["actual_value"] is None
    assert 70 < float(pj["predicted_value"]) < 100 and float(pj["predicted_cost"]) > 10
    lo, hi = pj["detail"]["interval_95_output_quantity"]
    assert lo < float(pj["predicted_value"]) < hi
    client.post(f"/api/v1/production-orders/{oid}/complete", headers=h, json={"outputs": [
        {"product_id": sucuk["id"], "lot_code": "SUC-2026-045", "quantity": "85", "unit_code": "PACK"}]})
    got = client.get(f"/api/v1/ai/predictions/{pj['id']}", headers=h).json()
    assert got["actual_value"] == "85.000000" and got["actual_cost"] == "18.1588"
    assert "deviation_quantity" in got["detail"] and got["metric_name"] == "ABS_ERROR_QUANTITY"


def test_butchering_prediction_parts_and_deviation(client, auth):
    h = auth("ADMIN")
    _train(client, h)
    r = client.post("/api/v1/ai/butchering-output/predict", headers=h, json={"animal_type": "KUZU", "input_weight": "25"})
    assert r.status_code == 200, r.text
    parts = r.json()["detail"]["parts"]
    assert {"BUT", "SIRT", "OMUZ", "FIRE"} <= set(parts)
    total = sum(p["predicted_weight"] for p in parts.values())
    assert 24 < total < 26  # oranlar yaklaşık 1'e toplanır
    assert client.post("/api/v1/ai/butchering-output/predict", headers=h, json={}).status_code == 400


def test_unknown_animal_uses_baseline_with_limitation(client, auth):
    h = auth("ADMIN")
    _train(client, h)
    r = client.post("/api/v1/ai/butchering-output/predict", headers=h, json={"animal_type": "DEVE", "input_weight": "100"})
    assert r.status_code == 200 and r.json()["detail"]["used_model"] is False
    assert "eğitim verisinde yok" in r.json()["limitations_note"]


def test_small_data_falls_back_to_baseline(client, auth):
    h = auth("ADMIN")
    r = client.post("/api/v1/ai/models/train", headers=h).json()
    assert r["production_yield"]["metrics"] is None and "baseline" in r["production_yield"]["version"]
    assert any("30" in l for l in r["production_yield"]["limitations"])


def test_ai_permissions(client, auth):
    assert client.post("/api/v1/ai/models/train", headers=auth("VIEWER")).status_code == 403
    assert client.post("/api/v1/ai/models/train", headers=auth("SALES")).status_code == 403
    assert client.get("/api/v1/ai/models", headers=auth("VIEWER")).status_code == 200
