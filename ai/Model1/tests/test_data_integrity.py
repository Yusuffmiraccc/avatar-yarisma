from pathlib import Path

import numpy as np
import pandas as pd

from training.validate_models import FEATURES_A, FEATURES_B, TARGET_COST, TARGET_EKP, TARGET_YIELD

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv"


def load_data():
    return pd.read_csv(DATA)


def test_synthetic_dataset_schema_is_unique_complete_and_expected_size():
    frame = load_data()
    assert frame.shape == (1000, 42)
    assert frame.columns.is_unique
    assert int(frame.isna().sum().sum()) == 0
    assert int(frame.duplicated().sum()) == 0
    assert int(frame["Parti_ID"].duplicated().sum()) == 0


def test_all_training_rows_are_explicitly_synthetic():
    frame = load_data()
    assert frame["Veri_sinifi"].notna().all()
    assert frame["Veri_sinifi"].str.contains("SENTET", case=False).all()


def test_targets_and_cost_inputs_are_physically_nonnegative():
    frame = load_data()
    nonnegative = [
        "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
        "Diger_kucuk_girdi_kg", "Kilif_metre", "Net_sucuk_ciktisi_kg_simule",
        "Toplam_parti_maliyeti_TL", "EKP_TL_kg",
    ]
    assert (frame[nonnegative] >= 0).all().all()
    assert (frame[["Net_sucuk_ciktisi_kg_simule", "Toplam_parti_maliyeti_TL", "EKP_TL_kg"]] > 0).all().all()


def test_mass_balance_matches_simulated_net_output_with_rounding_tolerance():
    frame = load_data()
    inputs = frame[["Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg", "Diger_kucuk_girdi_kg"]].sum(axis=1)
    predicted = inputs * (1 - frame["Kuruma_kaybi_pct"] / 100) * (1 - frame["Ayiklama_fire_pct"] / 100)
    assert float((predicted - frame[TARGET_YIELD]).abs().max()) <= 0.00051


def test_material_and_total_cost_reconciliation_with_cent_rounding():
    frame = load_data()
    material_parts = frame[["Et_maliyeti_TL", "Yag_maliyeti_TL", "Baharat_maliyeti_TL", "Tuz_diger_girdi_maliyeti_TL", "Kilif_maliyeti_TL"]].sum(axis=1)
    assert float((material_parts - frame["Direkt_malzeme_toplam_TL"]).abs().max()) <= 0.0201
    total_parts = frame[["Direkt_malzeme_toplam_TL", "Fason_hizmet_TL", "Kurum_ici_isleme_TL", "Paketleme_maliyeti_TL", "Genel_gider_TL"]].sum(axis=1)
    assert float((total_parts - frame[TARGET_COST]).abs().max()) <= 0.0201
    assert ((frame["Fason_hizmet_TL"] == 0) | (frame["Kurum_ici_isleme_TL"] == 0)).all()


def test_ekp_matches_total_cost_per_net_kg_with_rounding_tolerance():
    frame = load_data()
    ratio = frame[TARGET_COST] / frame[TARGET_YIELD]
    assert float((ratio - frame[TARGET_EKP]).abs().max()) <= 0.016


def test_model_feature_allowlists_exclude_targets_and_postproduction_fields():
    prohibited = {TARGET_COST, TARGET_YIELD, TARGET_EKP, "Iscilik_saati", "Elektrik_kWh", "Et_maliyet_payi_pct", "Karisim_girdi_toplam_kg"}
    assert not prohibited.intersection(FEATURES_A)
    assert not prohibited.intersection(FEATURES_B)
    assert set(FEATURES_B) - set(FEATURES_A) == {"Kuruma_kaybi_pct", "Ayiklama_fire_pct"}
