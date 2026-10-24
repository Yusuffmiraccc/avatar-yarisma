import numpy as np
import pytest

from training.compare_ekp_models import COST, TARGET, YIELD_TARGET, FEATURES
from training.compare_ekp_models_chronological import (
    SPLIT_DATE,
    chronological_holdout,
    expanding_date_splits,
    load_ordered_frame,
    _positive_finite,
)


def test_date_grouped_holdout_is_strictly_later_than_training():
    frame, _ = load_ordered_frame()
    train, test, metadata = chronological_holdout(frame)

    train_dates = set(train[SPLIT_DATE])
    test_dates = set(test[SPLIT_DATE])
    assert train_dates.isdisjoint(test_dates)
    assert max(train_dates) < min(test_dates)
    assert metadata["train_rows"] == len(train)
    assert metadata["test_rows"] == len(test)
    assert abs(metadata["actual_test_fraction_by_rows"] - 0.20) < 0.03


def test_expanding_cv_keeps_date_groups_and_never_uses_outer_holdout():
    frame, _ = load_ordered_frame()
    training, holdout, _ = chronological_holdout(frame)
    folds = expanding_date_splits(training, n_splits=5)

    assert len(folds) == 5
    for train_indices, valid_indices in folds:
        train_dates = set(training.iloc[train_indices][SPLIT_DATE])
        valid_dates = set(training.iloc[valid_indices][SPLIT_DATE])
        assert train_dates.isdisjoint(valid_dates)
        assert max(train_dates) < min(valid_dates)
        assert not valid_dates.intersection(set(holdout[SPLIT_DATE]))


def test_ekp_model_inputs_exclude_targets_realized_outputs_and_losses():
    forbidden = {
        TARGET, COST, YIELD_TARGET, "Kuruma_kaybi_pct", "Ayiklama_fire_pct",
        "Karisim_girdi_toplam_kg", "Tarih_simulasyon", "Parti_ID",
        "Iscilik_saati", "Elektrik_kWh", "Et_maliyet_payi_pct",
    }
    assert len(FEATURES) == 18
    assert not forbidden.intersection(FEATURES)


def test_cost_yield_ratio_rejects_nonpositive_or_nonfinite_components():
    with pytest.raises(ValueError, match="positive"):
        _positive_finite(np.array([10.0, 0.0]), "test value")
    with pytest.raises(ValueError, match="finite"):
        _positive_finite(np.array([10.0, np.inf]), "test value")



import pandas as pd
from training.compare_ekp_models import DATA
from training.report_ekp_data_quality import audit_frame


def test_synthetic_data_quality_audit_reconciles_targets_and_units():
    report = audit_frame(pd.read_csv(DATA))

    assert report["rows"] == 1000
    assert report["columns"] == 42
    assert len(report["column_profile"]) == 42
    assert report["all_synthetic"] is True
    assert report["missing_cells"] == 0
    assert report["duplicate_rows"] == 0
    assert report["duplicate_batch_ids"] == 0
    assert report["formula_checks"]["mass_balance_max_abs_kg"] < 0.00051
    assert report["formula_checks"]["total_cost_max_abs_tl"] <= 0.0201
    assert report["formula_checks"]["ekp_max_abs_tl_kg"] < 0.016

