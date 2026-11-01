from fastapi.testclient import TestClient
import joblib
import pytest
import pandas as pd
from sklearn.dummy import DummyRegressor
from app.main import app
import app.main as main_module

client = TestClient(app)


def valid_prediction_payload():
    return {
        "Et_girdi_kg": 200, "Kuyruk_yagi_girdi_kg": 40, "Baharat_girdi_kg": 12,
        "Tuz_girdi_kg": 4, "Diger_kucuk_girdi_kg": 1, "Kilif_metre": 300,
        "Et_fiyat_TL_kg": 590, "Kuyruk_yagi_fiyat_TL_kg": 420,
        "Baharat_fiyat_TL_kg": 400, "Tuz_fiyat_TL_kg": 20, "Kilif_fiyat_TL_m": 44,
        "Fason_birim_bedel_TL_kg_girdi": 100, "Iscilik_maliyeti_TL_saat": 175,
        "Elektrik_fiyati_TL_kWh": 4.8, "Ambalaj_TL_kg_net_urun": 5.5,
        "Bolge": "İç Anadolu", "Recete_profili": "MEB_STANDART", "Isleme_modeli": "Fason",
    }

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_model_status_explains_second_model():
    response = client.get("/v1/models/status")
    assert response.status_code == 200
    assert response.json()["lamb_cutting_model"] == "not_available"
    assert response.json()["ekp_production_ready"] is False
    assert response.json()["ekp_warning"]

def test_production_evaluation_returns_prediction_actual_and_deviation():
    response = client.post(
        "/v1/evaluate/production",
        json={
            "predicted_net_output_kg": 85.0,
            "actual_net_output_kg": 82.0,
            "predicted_ekp_tl_per_kg": 180.0,
            "actual_total_cost_tl": 15170.0,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["predicted_net_output_kg"] == 85.0
    assert data["actual_net_output_kg"] == 82.0
    assert data["yield_deviation_kg"] == 3.0
    assert data["predicted_ekp_tl_per_kg"] == 180.0
    assert data["actual_total_cost_tl"] == 15170.0
    assert data["actual_ekp_tl_per_kg"] == 185.0
    assert data["ekp_deviation_tl_per_kg"] == -5.0
    assert "tahmin - gerçekleşen" in data["deviation_convention"]


def test_production_evaluation_rejects_zero_actual_output():
    response = client.post(
        "/v1/evaluate/production",
        json={
            "predicted_net_output_kg": 85.0,
            "actual_net_output_kg": 0.0,
            "predicted_ekp_tl_per_kg": 180.0,
            "actual_total_cost_tl": 15170.0,
        },
    )

    assert response.status_code == 422


def test_production_evaluation_rejects_unexpected_fields():
    response = client.post(
        "/v1/evaluate/production",
        json={
            "predicted_net_output_kg": 85.0,
            "actual_net_output_kg": 82.0,
            "predicted_ekp_tl_per_kg": 180.0,
            "actual_total_cost_tl": 15170.0,
            "unexpected_field": 123,
        },
    )

    assert response.status_code == 422


def test_production_evaluation_rejects_missing_wrong_type_nonfinite_and_negative_values():
    base = {
        "predicted_net_output_kg": 85.0,
        "actual_net_output_kg": 82.0,
        "predicted_ekp_tl_per_kg": 180.0,
        "actual_total_cost_tl": 15170.0,
    }
    missing = dict(base)
    missing.pop("actual_total_cost_tl")
    assert client.post("/v1/evaluate/production", json=missing).status_code == 422
    wrong_type = dict(base, actual_total_cost_tl="cost")
    assert client.post("/v1/evaluate/production", json=wrong_type).status_code == 422
    negative = dict(base, actual_total_cost_tl=-1)
    assert client.post("/v1/evaluate/production", json=negative).status_code == 422
    zero_cost = dict(base, actual_total_cost_tl=0)
    assert client.post("/v1/evaluate/production", json=zero_cost).status_code == 422
    for literal in ("NaN", "Infinity", "-Infinity"):
        invalid = '{"predicted_net_output_kg":85,"actual_net_output_kg":82,"predicted_ekp_tl_per_kg":180,"actual_total_cost_tl":' + literal + '}'
        response = client.post("/v1/evaluate/production", content=invalid, headers={"content-type": "application/json"})
        assert response.status_code == 422


def test_production_evaluation_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(main_module, "API_KEY", "test-secret")
    payload = {
        "predicted_net_output_kg": 85.0,
        "actual_net_output_kg": 82.0,
        "predicted_ekp_tl_per_kg": 180.0,
        "actual_total_cost_tl": 15170.0,
    }
    assert client.post("/v1/evaluate/production", json=payload).status_code == 401
    response = client.post("/v1/evaluate/production", json=payload, headers={"x-api-key": "test-secret"})
    assert response.status_code == 200
    monkeypatch.setattr(main_module, "API_KEY", "")


def test_prediction_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(main_module, "API_KEY", "test-secret")
    response = client.post("/v1/predict/production", json=valid_prediction_payload())
    assert response.status_code == 401
    assert client.post("/v1/predict/production", json=valid_prediction_payload(), headers={"x-api-key": "wrong"}).status_code == 401
    monkeypatch.setattr(main_module, "API_KEY", "")


def test_missing_api_key_fails_closed_outside_development(monkeypatch):
    monkeypatch.setattr(main_module, "API_KEY", "")
    monkeypatch.setattr(main_module, "APP_ENV", "production")
    response = client.post("/v1/predict/production", json=valid_prediction_payload())
    assert response.status_code == 503
    assert "yapılandırılmamış" in response.json()["detail"]
    monkeypatch.setattr(main_module, "APP_ENV", "development")


def test_prediction_uses_allowlisted_model_columns_and_warns(monkeypatch):
    class FakeModel:
        def predict(self, frame):
            assert "Toplam_parti_maliyeti_TL" not in frame.columns
            assert "EKP_TL_kg" not in frame.columns
            assert "Kuruma_kaybi_pct" not in frame.columns
            return [100.0]

    monkeypatch.setattr(main_module, "_load_model", lambda filename: {"model": FakeModel()})
    payload = {
        "Et_girdi_kg": 200, "Kuyruk_yagi_girdi_kg": 40, "Baharat_girdi_kg": 12,
        "Tuz_girdi_kg": 4, "Diger_kucuk_girdi_kg": 1, "Kilif_metre": 300,
        "Et_fiyat_TL_kg": 590, "Kuyruk_yagi_fiyat_TL_kg": 420,
        "Baharat_fiyat_TL_kg": 400, "Tuz_fiyat_TL_kg": 20, "Kilif_fiyat_TL_m": 44,
        "Fason_birim_bedel_TL_kg_girdi": 100, "Iscilik_maliyeti_TL_saat": 175,
        "Elektrik_fiyati_TL_kWh": 4.8, "Ambalaj_TL_kg_net_urun": 5.5,
        "Genel_gider_TL": 3500, "Bolge": "İç Anadolu", "Recete_profili": "MEB_STANDART",
        "Isleme_modeli": "Fason",
    }
    response = client.post("/v1/predict/production", json=payload)
    assert response.status_code == 200
    assert response.json()["predicted_net_output_kg"] == 100.0
    assert "hazır değildir" in response.json()["model_notice"]


def test_prediction_rejects_nonfinite_and_wrong_types():
    bad_number = '{"Et_girdi_kg": NaN}'
    assert client.post("/v1/predict/production", content=bad_number, headers={"content-type": "application/json"}).status_code == 422
    assert client.post("/v1/predict/production", json={"Et_girdi_kg": "not-a-number"}).status_code == 422
    assert client.post("/v1/predict/production", json={"Et_girdi_kg": -1}).status_code == 422
    assert client.post("/v1/predict/production", json={"Et_girdi_kg": 1}).status_code == 422  # required fields missing
    assert client.post("/v1/predict/production", json=dict(valid_prediction_payload(), unexpected="field")).status_code == 422
    for literal in ("Infinity", "-Infinity"):
        invalid = '{"Et_girdi_kg":' + literal + '}'
        response = client.post("/v1/predict/production", content=invalid, headers={"content-type": "application/json"})
        assert response.status_code == 422


def test_missing_or_unreadable_model_returns_safe_503(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "MODEL_DIR", tmp_path)
    missing = client.post("/v1/predict/production", json=valid_prediction_payload())
    assert missing.status_code == 503
    assert "kurulu değil" in missing.json()["detail"]
    assert str(tmp_path) not in missing.text

    (tmp_path / "yield_model.joblib").write_bytes(b"not a joblib model")
    unreadable = client.post("/v1/predict/production", json=valid_prediction_payload())
    assert unreadable.status_code == 503
    assert "yüklenemedi" in unreadable.json()["detail"]
    assert str(tmp_path) not in unreadable.text


def test_prediction_loads_model_bundles_from_model_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "MODEL_DIR", tmp_path)
    for filename, target in (("yield_model.joblib", 90.0), ("ekp_model.joblib", 210.0)):
        estimator = DummyRegressor(strategy="constant", constant=target)
        estimator.fit(pd.DataFrame({"Et_girdi_kg": [1.0, 2.0]}), [target, target])
        joblib.dump({"model": estimator, "feature_columns": ["Et_girdi_kg"]}, tmp_path / filename)

    payload = {
        "Et_girdi_kg": 200, "Kuyruk_yagi_girdi_kg": 40, "Baharat_girdi_kg": 12,
        "Tuz_girdi_kg": 4, "Diger_kucuk_girdi_kg": 1, "Kilif_metre": 300,
        "Et_fiyat_TL_kg": 590, "Kuyruk_yagi_fiyat_TL_kg": 420,
        "Baharat_fiyat_TL_kg": 400, "Tuz_fiyat_TL_kg": 20, "Kilif_fiyat_TL_m": 44,
        "Fason_birim_bedel_TL_kg_girdi": 100, "Iscilik_maliyeti_TL_saat": 175,
        "Elektrik_fiyati_TL_kWh": 4.8, "Ambalaj_TL_kg_net_urun": 5.5,
        "Bolge": "İç Anadolu", "Recete_profili": "MEB_STANDART", "Isleme_modeli": "Fason",
    }
    response = client.post("/v1/predict/production", json=payload)
    assert response.status_code == 200
    assert response.json()["predicted_net_output_kg"] == 90.0
    assert response.json()["predicted_ekp_tl_per_kg"] == 210.0


@pytest.mark.skipif(
    not (main_module.MODEL_DIR / "yield_model.joblib").exists(),
    reason="üretim modeli kurulu değil (training.train_production sonrası aday dosyaları terfi ettirin)",
)
def test_existing_api_models_load_and_predict():
    response = client.post("/v1/predict/production", json=valid_prediction_payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["predicted_net_output_kg"] > 0
    assert data["predicted_ekp_tl_per_kg"] > 0
    assert "hazır değildir" in data["model_notice"]


def test_prediction_rejects_numeric_strings_booleans_and_unknown_categories():
    payload = valid_prediction_payload()
    for field in ("Et_girdi_kg", "Iscilik_maliyeti_TL_saat"):
        invalid = dict(payload, **{field: "200"})
        assert client.post("/v1/predict/production", json=invalid).status_code == 422
    assert client.post("/v1/predict/production", json=dict(payload, Et_girdi_kg=True)).status_code == 422
    for field, value in (("Bolge", "Anadolu"), ("Recete_profili", "BILINMEYEN"), ("Isleme_modeli", "bilinmiyor")):
        assert client.post("/v1/predict/production", json=dict(payload, **{field: value})).status_code == 422


def test_evaluation_rejects_numeric_strings_and_booleans():
    payload = {
        "predicted_net_output_kg": 85,
        "actual_net_output_kg": 82,
        "predicted_ekp_tl_per_kg": 180,
        "actual_total_cost_tl": 15170,
    }
    for field, value in (("actual_net_output_kg", "82"), ("actual_total_cost_tl", True)):
        assert client.post("/v1/evaluate/production", json=dict(payload, **{field: value})).status_code == 422


def test_prediction_rejects_nonfinite_and_physically_impossible_model_outputs(monkeypatch):
    class FakeModel:
        def __init__(self, value):
            self.value = value

        def predict(self, frame):
            return [self.value]

    payload = valid_prediction_payload()
    for yield_value, ekp_value in ((float("nan"), 200.0), (300.0, 200.0), (100.0, float("inf")), (100.0, -1.0)):
        monkeypatch.setattr(
            main_module, "_load_model",
            lambda filename: {"model": FakeModel(yield_value if filename.startswith("yield") else ekp_value)},
        )
        response = client.post("/v1/predict/production", json=payload)
        assert response.status_code == 503
        assert "fiziksel olarak geçersiz" in response.json()["detail"]
