import numpy as np
import pandas as pd
import joblib
import pytest

from training.compare_ekp_models import (
    DATA,
    EXTRA,
    FEATURES,
    PlannedCostFeatures,
    load_frame,
)
from training.compare_ekp_models import CANDIDATE_PATH


def test_ekp_engineered_features_use_only_allowlisted_inputs():
    source = pd.read_csv(DATA)
    fason_index = source.index[source["Isleme_modeli"].astype(str).str.contains("Fason", case=False)][0]
    inhouse_index = source.index[~source["Isleme_modeli"].astype(str).str.contains("Fason", case=False)][0]
    inputs = source.loc[[fason_index, inhouse_index], FEATURES].copy()

    result = PlannedCostFeatures().fit_transform(inputs)

    assert set(EXTRA).issubset(result.columns)
    assert not {"EKP_TL_kg", "Toplam_parti_maliyeti_TL", "Net_sucuk_ciktisi_kg_simule",
                "Kuruma_kaybi_pct", "Ayiklama_fire_pct"}.intersection(result.columns)

    input_kg = inputs[
        ["Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg",
         "Tuz_girdi_kg", "Diger_kucuk_girdi_kg"]
    ].sum(axis=1)
    direct_material = (
        inputs["Et_girdi_kg"] * inputs["Et_fiyat_TL_kg"]
        + inputs["Kuyruk_yagi_girdi_kg"] * inputs["Kuyruk_yagi_fiyat_TL_kg"]
        + inputs["Baharat_girdi_kg"] * inputs["Baharat_fiyat_TL_kg"]
        + inputs["Kilif_metre"] * inputs["Kilif_fiyat_TL_m"]
    )
    expected_service = np.where(
        inputs["Isleme_modeli"].astype(str).str.contains("Fason", case=False),
        input_kg * inputs["Fason_birim_bedel_TL_kg_girdi"],
        0,
    )
    np.testing.assert_allclose(result["Planlanan_girdi_toplam_kg"], input_kg)
    np.testing.assert_allclose(
        result["Dogrulanmis_malzeme_fason_TL"], direct_material + expected_service
    )


def test_ekp_comparison_data_is_explicitly_synthetic_and_formula_consistent():
    frame, checks = load_frame()

    assert checks["all_rows_synthetic"] is True
    assert len(frame) == 1000
    assert checks["missing_required_cells"] == 0
    assert checks["ekp_formula_max_abs_diff_tl_kg"] < 0.016
    assert checks["fason_rate_max_abs_diff_tl"] <= 0.0051


@pytest.mark.skipif(not CANDIDATE_PATH.exists(), reason="aday model eğitilmedi (training.compare_ekp_models)")
def test_ekp_research_candidate_is_separate_and_loads_finite_predictions():
    package = joblib.load(CANDIDATE_PATH)
    assert package["data_type"] == "synthetic"
    assert package["production_ready"] is False
    assert package["feature_columns"] == FEATURES
    assert package["training_records"] == 800

    source = pd.read_csv(DATA)
    predictions = package["model"].predict(source[FEATURES].head(5))
    assert np.isfinite(predictions).all()
    assert np.all(predictions > 0)

