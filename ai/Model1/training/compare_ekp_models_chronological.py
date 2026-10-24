"""Leakage-aware, date-grouped EKP research comparison on synthetic data.

A final trailing-date holdout is kept out of model selection. No model artifacts are
loaded or written by this experiment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.model_selection import TimeSeriesSplit

from .compare_ekp_models import (
    COST, DATA, FEATURES, PRODUCTION, REPORTS, TARGET, YIELD_TARGET,
    load_frame, known_subtotal, pipe, score,
)

DATE_FIELD = "Tarih_simulasyon"
SPLIT_DATE = "_split_date"
RANDOM_STATE = 42
TEST_FRACTION = 0.20
N_CV_SPLITS = 5


def load_ordered_frame() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the checked synthetic data and sort by its generated calendar date."""
    frame, checks = load_frame()
    if DATE_FIELD not in frame:
        raise ValueError(f"Missing simulated date field: {DATE_FIELD}")
    dates = pd.to_datetime(frame[DATE_FIELD], errors="coerce")
    if dates.isna().any():
        raise ValueError("All simulation dates must parse for grouped chronological evaluation")
    frame = frame.copy()
    frame[SPLIT_DATE] = dates.dt.strftime("%Y-%m-%d")
    return frame.sort_values(SPLIT_DATE, kind="mergesort").reset_index(drop=True), checks


def chronological_holdout(
    frame: pd.DataFrame, test_fraction: float = TEST_FRACTION, min_train_dates: int = 6
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Choose trailing whole-date groups nearest the requested row share."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    if SPLIT_DATE not in frame:
        raise ValueError(f"Frame must contain {SPLIT_DATE}")
    dates = sorted(frame[SPLIT_DATE].dropna().astype(str).unique())
    if len(dates) <= min_train_dates:
        raise ValueError(f"Need more than {min_train_dates} distinct dates")
    target_rows = round(len(frame) * test_fraction)
    choices = []
    for n_test_dates in range(1, len(dates) - min_train_dates + 1):
        cutoff = dates[-n_test_dates]
        n_test = int(frame[SPLIT_DATE].ge(cutoff).sum())
        choices.append((abs(n_test - target_rows), n_test_dates, cutoff, n_test))
    _, n_test_dates, cutoff, _ = min(choices, key=lambda row: (row[0], row[1]))
    train = frame.loc[frame[SPLIT_DATE] < cutoff].copy().reset_index(drop=True)
    test = frame.loc[frame[SPLIT_DATE] >= cutoff].copy().reset_index(drop=True)
    if train.empty or test.empty or max(train[SPLIT_DATE]) >= min(test[SPLIT_DATE]):
        raise ValueError("Train/test split does not preserve strict chronology")
    train_dates, test_dates = sorted(train[SPLIT_DATE].unique()), sorted(test[SPLIT_DATE].unique())
    return train, test, {
        "method": "trailing date-group holdout",
        "requested_test_fraction_by_rows": test_fraction,
        "actual_test_fraction_by_rows": len(test) / len(frame),
        "train_rows": len(train),
        "test_rows": len(test),
        "distinct_dates_total": len(dates),
        "train_distinct_dates": len(train_dates),
        "test_distinct_dates": len(test_dates),
        "train_date_start": train_dates[0],
        "train_date_end": train_dates[-1],
        "test_date_start": test_dates[0],
        "test_date_end": test_dates[-1],
        "holdout_cutoff": cutoff,
        "train_dates": train_dates,
        "test_dates": test_dates,
    }


def expanding_date_splits(training: pd.DataFrame, n_splits: int = N_CV_SPLITS):
    """Expanding folds over whole distinct dates, using only outer-training rows."""
    dates = np.array(sorted(training[SPLIT_DATE].astype(str).unique()))
    if len(dates) < n_splits + 2:
        raise ValueError(f"Need at least {n_splits + 2} dates; got {len(dates)}")
    date_series = pd.Series(training[SPLIT_DATE].astype(str))
    splits = []
    for train_groups, valid_groups in TimeSeriesSplit(n_splits=n_splits).split(dates):
        train_dates, valid_dates = set(dates[train_groups]), set(dates[valid_groups])
        train_idx = np.flatnonzero(date_series.isin(train_dates).to_numpy())
        valid_idx = np.flatnonzero(date_series.isin(valid_dates).to_numpy())
        if not len(train_idx) or not len(valid_idx):
            raise ValueError("An expanding date fold is empty")
        if max(date_series.iloc[train_idx]) >= min(date_series.iloc[valid_idx]):
            raise ValueError("A fold crosses or reverses date chronology")
        splits.append((train_idx, valid_idx))
    return splits


def model_specs():
    """Fixed settings declared before holdout evaluation; no holdout-driven tuning."""
    rf = RandomForestRegressor(
        n_estimators=350, min_samples_leaf=2, max_features=0.9,
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    return {
        "median_baseline": pipe(DummyRegressor(strategy="median")),
        "mean_baseline": pipe(DummyRegressor(strategy="mean")),
        "random_forest_incumbent_architecture": pipe(rf),
        "extra_trees": pipe(ExtraTreesRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=RANDOM_STATE, n_jobs=-1,
        )),
        "gradient_boosting_huber": pipe(GradientBoostingRegressor(
            loss="huber", n_estimators=160, learning_rate=0.03,
            max_depth=2, min_samples_leaf=5, random_state=RANDOM_STATE,
        )),
        "hist_gradient_boosting": pipe(HistGradientBoostingRegressor(
            max_iter=150, max_leaf_nodes=15, learning_rate=0.05,
            l2_regularization=1.0, random_state=RANDOM_STATE,
        )),
        "ridge": pipe(Ridge(alpha=10.0), scale_numeric=True),
        "huber_regressor": pipe(
            HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=1000),
            scale_numeric=True,
        ),
        "engineered_gradient_boosting_huber": pipe(
            GradientBoostingRegressor(
                loss="huber", n_estimators=160, learning_rate=0.03,
                max_depth=2, min_samples_leaf=5, random_state=RANDOM_STATE,
            ),
            engineered=True,
        ),
    }


def _positive_finite(values: np.ndarray, label: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError(f"{label} must be finite and positive for EKP calculation")
    return values


def _cost_yield(train_x, valid_x, train_cost, train_yield) -> np.ndarray:
    rf = RandomForestRegressor(
        n_estimators=350, min_samples_leaf=2, max_features=0.9,
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    cost_model = clone(pipe(rf)).fit(train_x, train_cost)
    yield_model = clone(pipe(rf)).fit(train_x, train_yield)
    return _positive_finite(cost_model.predict(valid_x), "Predicted cost") / _positive_finite(
        yield_model.predict(valid_x), "Predicted net output"
    )


def _hybrid(train_x, valid_x, train_cost, train_yield) -> np.ndarray:
    rf = RandomForestRegressor(
        n_estimators=350, min_samples_leaf=2, max_features=0.9,
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    known_train = known_subtotal(train_x).astype(float)
    known_valid = known_subtotal(valid_x).astype(float)
    residual = train_cost.to_numpy(dtype=float) - known_train.to_numpy(dtype=float)
    cost_model = clone(pipe(rf, engineered=True)).fit(train_x, residual)
    yield_model = clone(pipe(rf)).fit(train_x, train_yield)
    total = known_valid.to_numpy(dtype=float) + cost_model.predict(valid_x)
    return _positive_finite(total, "Hybrid predicted cost") / _positive_finite(
        yield_model.predict(valid_x), "Predicted net output"
    )


def _metric_delta(metrics, baseline):
    result = dict(metrics)
    for key in ("mae_tl_kg", "rmse_tl_kg"):
        result[f"{key}_change_vs_training_median_baseline"] = result[key] - baseline[key]
        result[f"{key}_improvement_vs_training_median_baseline_pct"] = (
            100.0 * (baseline[key] - result[key]) / baseline[key] if baseline[key] else None
        )
    return result


def _sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _historical_results():
    path = REPORTS / "ekp_improvement_comparison.json"
    if not path.is_file():
        return {"available": False}
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False, "reason": "Prior comparison JSON could not be parsed"}
    validation = prior.get("validation", {})
    return {
        "available": True,
        "report": "reports/ekp_improvement_comparison.json",
        "comparability": "historical shuffled evaluation; not directly comparable to date-group holdout",
        "cross_validation": validation.get("cv", {}).get("metrics", {}),
        "fixed_holdout": validation.get("secondary_holdout", {}).get("metrics", {}),
        "production_artifact": validation.get("production_artifact", {}),
        "previous_candidate": validation.get("previous_candidate", {}),
    }


def run_comparison(test_fraction: float = TEST_FRACTION, n_splits: int = N_CV_SPLITS):
    frame, integrity = load_ordered_frame()
    training, test, split = chronological_holdout(frame, test_fraction)
    x_train, y_train = training[FEATURES].copy(), training[TARGET].astype(float)
    cost_train, yield_train = training[COST].astype(float), training[YIELD_TARGET].astype(float)
    x_test, y_test = test[FEATURES].copy(), test[TARGET].astype(float)
    specs = model_specs()
    folds = expanding_date_splits(training, n_splits)
    cv_scores = {name: [] for name in specs}
    cv_scores["predicted_cost_over_predicted_yield_rf"] = []
    cv_scores["hybrid_known_cost_plus_residual_over_predicted_yield_rf"] = []
    fold_info = []

    for fold_no, (train_idx, valid_idx) in enumerate(folds, start=1):
        xtr, xval = x_train.iloc[train_idx], x_train.iloc[valid_idx]
        ytr, yval = y_train.iloc[train_idx], y_train.iloc[valid_idx]
        ctr, yitr = cost_train.iloc[train_idx], yield_train.iloc[train_idx]
        train_dates = sorted(training.iloc[train_idx][SPLIT_DATE].unique())
        valid_dates = sorted(training.iloc[valid_idx][SPLIT_DATE].unique())
        fold_info.append({
            "fold": fold_no, "train_rows": len(train_idx), "validation_rows": len(valid_idx),
            "train_date_start": train_dates[0], "train_date_end": train_dates[-1],
            "validation_date_start": valid_dates[0], "validation_date_end": valid_dates[-1],
        })
        for name, spec in specs.items():
            fitted = clone(spec).fit(xtr, ytr)
            cv_scores[name].append(score(yval, fitted.predict(xval)))
        cv_scores["predicted_cost_over_predicted_yield_rf"].append(
            score(yval, _cost_yield(xtr, xval, ctr, yitr))
        )
        cv_scores["hybrid_known_cost_plus_residual_over_predicted_yield_rf"].append(
            score(yval, _hybrid(xtr, xval, ctr, yitr))
        )

    cv = {}
    for name, values in cv_scores.items():
        cv[name] = {
            metric: {
                "mean": float(np.mean([item[metric] for item in values])),
                "std": float(np.std([item[metric] for item in values], ddof=1)),
                "fold_values": [float(item[metric]) for item in values],
            }
            for metric in ("mae_tl_kg", "rmse_tl_kg", "r2")
        }
    baseline_cv_mae = cv["median_baseline"]["mae_tl_kg"]["mean"]
    for values in cv.values():
        values["mae_improvement_vs_median_baseline_pct"] = float(
            100.0 * (baseline_cv_mae - values["mae_tl_kg"]["mean"]) / baseline_cv_mae
        )
    ranking = sorted(
        (name for name in cv if name not in {"median_baseline", "mean_baseline"}),
        key=lambda name: cv[name]["mae_tl_kg"]["mean"],
    )

    median_baseline = score(y_test, np.full(len(y_test), float(y_train.median())))
    mean_baseline = score(y_test, np.full(len(y_test), float(y_train.mean())))
    holdout = {"median_baseline": median_baseline, "mean_baseline": mean_baseline}
    for name, spec in specs.items():
        fitted = clone(spec).fit(x_train, y_train)
        holdout[name] = score(y_test, fitted.predict(x_test))
    holdout["predicted_cost_over_predicted_yield_rf"] = score(
        y_test, _cost_yield(x_train, x_test, cost_train, yield_train)
    )
    holdout["hybrid_known_cost_plus_residual_over_predicted_yield_rf"] = score(
        y_test, _hybrid(x_train, x_test, cost_train, yield_train)
    )
    for values in holdout.values():
        values.update(_metric_delta(values, median_baseline))

    model_rows = []
    for name, metrics in cv.items():
        test_metrics = holdout[name]
        model_rows.append({
            "model": name,
            "cv_mae_mean_tl_kg": metrics["mae_tl_kg"]["mean"],
            "cv_mae_std_tl_kg": metrics["mae_tl_kg"]["std"],
            "cv_rmse_mean_tl_kg": metrics["rmse_tl_kg"]["mean"],
            "cv_rmse_std_tl_kg": metrics["rmse_tl_kg"]["std"],
            "cv_r2_mean": metrics["r2"]["mean"],
            "cv_r2_std": metrics["r2"]["std"],
            "cv_mae_improvement_vs_median_baseline_pct": metrics["mae_improvement_vs_median_baseline_pct"],
            "holdout_mae_tl_kg": test_metrics["mae_tl_kg"],
            "holdout_rmse_tl_kg": test_metrics["rmse_tl_kg"],
            "holdout_r2": test_metrics["r2"],
            "holdout_mae_change_vs_training_median_baseline": test_metrics["mae_tl_kg_change_vs_training_median_baseline"],
            "holdout_mae_improvement_vs_training_median_baseline_pct": test_metrics["mae_tl_kg_improvement_vs_training_median_baseline_pct"],
            "holdout_rmse_change_vs_training_median_baseline": test_metrics["rmse_tl_kg_change_vs_training_median_baseline"],
            "holdout_rmse_improvement_vs_training_median_baseline_pct": test_metrics["rmse_tl_kg_improvement_vs_training_median_baseline_pct"],
        })

    model_dir = PRODUCTION.parent
    artifacts = {
        "ekp_production_model": {
            "path": "models/ekp_model.joblib", "sha256": _sha256(PRODUCTION),
            "scored_on_new_holdout": False,
            "reason": "Training row/date provenance is not sufficient to prove the trailing dates were unseen; artifact was not deserialized.",
        },
        "yield_production_model": {
            "path": "models/yield_model.joblib", "sha256": _sha256(model_dir / "yield_model.joblib"),
            "scored_on_new_holdout": False, "artifact_loaded": False,
        },
        "saved_research_candidate": {
            "path": "models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib",
            "sha256": _sha256(model_dir / "candidates" / "ekp_gradient_boosting_huber_engineered_20261024.joblib"),
            "scored_on_new_holdout": False,
            "reason": "Prior shuffled fit does not record row/date membership; artifact was not deserialized.",
        },
        "artifacts_written_or_replaced": False,
    }
    return {
        "schema_version": "1.0",
        "dataset": str(DATA.relative_to(Path(__file__).resolve().parents[1])).replace("\\", "/"),
        "dataset_sha256": _sha256(DATA),
        "data_type": "synthetic/simulated only", "real_factory_validation": False,
        "target": TARGET, "target_definition": "total batch cost TRY / simulated net output kg = TRY/kg",
        "integrity_checks": integrity, "split": split,
        "features": FEATURES,
        "scenario_A_timing": "18 planned inputs/category/quote fields; actual preproduction snapshots are not verified.",
        "scenario_B": {
            "status": "diagnostic only, not a preproduction candidate",
            "additional_features": ["Kuruma_kaybi_pct", "Ayiklama_fire_pct"],
            "reason": "The workbook says these values are simulated; actual measurement/availability timing is unknown.",
        },
        "validation": {
            "method": "Expanding-window cross-validation over whole simulated dates, inside the earlier training dates only.",
            "n_splits": n_splits, "random_state": RANDOM_STATE,
            "preprocessing_fitted_inside_each_fold": True,
            "outer_holdout_used_for_selection": False,
            "folds": fold_info, "cv_metrics": cv, "ranking_by_cv_mae": ranking,
            "selected_cv_leader": ranking[0] if ranking else None,
        },
        "holdout_metrics": holdout, "candidate_metrics": model_rows,
        "parameters": {
            "settings": "Fixed estimator settings; no parameter search on the outer holdout.",
            "random_forest_and_extra_trees": "n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42",
            "gradient_boosting_huber": "n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=5, random_state=42",
            "hist_gradient_boosting": "max_iter=150, max_leaf_nodes=15, learning_rate=0.05, l2_regularization=1.0, random_state=42",
            "ridge": "alpha=10; numeric scaling inside pipeline",
            "huber_regressor": "epsilon=1.35, alpha=0.0001, max_iter=1000; numeric scaling inside pipeline",
        },
        "historical_shuffled_results": _historical_results(),
        "existing_artifacts": artifacts,
        "decision": {
            "production_model_changed": False, "candidate_model_written": False,
            "ekp_production_ready": False,
            "reason": "Synthetic-only data and simulated calendar dates cannot establish factory performance or temporal generalization.",
        },
        "limitations": [
            "All 1,000 records are synthetic/simulated; no real factory validation was performed.",
            "Tarih_simulasyon is generated simulation metadata, not a verified factory chronology; grouped splitting is only a leakage-resistant experiment on these synthetic dates.",
            "Preproduction availability of recipe, inputs, prices, tariffs, and process mode requires timestamped plan snapshots.",
            "Realized net output, cost, costs components, and loss fields are excluded from Scenario A features.",
            "Cost/yield and hybrid predictions train on earlier fold targets only; test cost/output are used only for evaluation.",
            "The hybrid known-cost subtotal is not confirmed against a real accounting policy.",
            "Artifact SHA-256 values identify local bytes but are not proof of source authenticity or scientific validity.",
        ],
    }


def write_outputs(report):
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "ekp_model_comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(report["candidate_metrics"]).sort_values(
        ["cv_mae_mean_tl_kg", "model"], kind="stable"
    ).to_csv(REPORTS / "ekp_model_comparison.csv", index=False, encoding="utf-8-sig")

    split = report["split"]
    lines = [
        "# EKP model comparison — chronological research evaluation", "",
        "Data notice: All 1,000 rows are synthetic/simulated. No real factory evaluation was performed.", "",
        "## Target and split", "",
        f"- Target: {report['target_definition']}.",
        f"- Dataset SHA-256: {report['dataset_sha256']}.",
        f"- Train: {split['train_rows']} rows, {split['train_date_start']} to {split['train_date_end']}.",
        f"- Holdout: {split['test_rows']} rows, {split['test_date_start']} to {split['test_date_end']}; whole dates remain together.",
        f"- Model selection: {report['validation']['n_splits']} expanding date folds inside training dates only; holdout did not select estimators.",
        "- The dates are generated simulation dates, not a real factory timeline.", "",
        "## Comparison", "",
        "CV values are mean ± fold standard deviation. Each candidate uses the same trailing-date holdout. "
        "Holdout change is model minus training-median baseline; positive means larger error. Improvement percentage is baseline-relative.", "",
        "| Model | CV MAE | CV RMSE | CV R² | Holdout MAE | Holdout RMSE | Holdout R² | MAE improvement vs median |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(report["candidate_metrics"], key=lambda item: item["cv_mae_mean_tl_kg"]):
        lines.append(
            f"| {row['model']} | {row['cv_mae_mean_tl_kg']:.4f} ± {row['cv_mae_std_tl_kg']:.4f} | "
            f"{row['cv_rmse_mean_tl_kg']:.4f} ± {row['cv_rmse_std_tl_kg']:.4f} | "
            f"{row['cv_r2_mean']:.4f} ± {row['cv_r2_std']:.4f} | "
            f"{row['holdout_mae_tl_kg']:.4f} | {row['holdout_rmse_tl_kg']:.4f} | "
            f"{row['holdout_r2']:.4f} | {row['holdout_mae_improvement_vs_training_median_baseline_pct']:.2f}% |"
        )
    lines += [
        "", f"CV leader by MAE: {report['validation']['selected_cv_leader']}; synthetic research ranking only.", "",
        "## Methods and leakage controls", "",
        "- Compared median and mean baselines, the incumbent Random Forest architecture, Extra Trees, Huber Gradient Boosting, HistGradientBoosting, Ridge, HuberRegressor, and the prior engineered Huber GradientBoosting architecture.",
        "- Also compared predicted total cost / predicted net output and a planned known-cost subtotal plus predicted residual divided by predicted net output. Component estimators were fit on training rows only.",
        "- Imputation, scaling, and one-hot encoding are in pipelines fit separately within each fold.",
        "- Scenario A uses the 18 allow-listed input, category, and quote/tariff fields; their real preproduction timing is not verified.",
        "- Scenario B loss rates are simulated and timing is unverified; they are not part of the candidate ranking.",
        "- Target, realized net output, total cost, cost components, and loss percentages are excluded from Scenario A features.", "",
        "## Existing artifacts", "",
        "Production and saved candidate artifacts were not deserialized or changed. Their training date membership is unavailable, so their scores are not represented as unseen-date results. Hashes and reasons are in the JSON report.",
        "Existing shuffled-split reports are retained as historical results and are not directly comparable to this split.", "",
        "## Decision", "",
        "No EKP model is recommended for production. Real factory data, verified feature timing, and an untouched site/time validation are still required.",
        "Repeat from the Model1 directory: python -m training.compare_ekp_models_chronological.",
        "Machine-readable reports: reports/ekp_model_comparison.json and reports/ekp_model_comparison.csv.",
    ]
    (REPORTS / "ekp_model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report = run_comparison()
    write_outputs(report)
    print(json.dumps({
        "status": "complete_synthetic_research_only",
        "split": report["split"],
        "cv_leader": report["validation"]["selected_cv_leader"],
        "metrics": report["candidate_metrics"],
        "model_artifacts_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

