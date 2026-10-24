"""Chronological EKP evaluation for validated, explicitly real production batches only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.production_data import (
    MODEL1_FEATURE_MAP,
    calculate_ekp,
    model1_scenario_a_features,
    validate_records,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "templates" / "real_production_batches_template.csv"
DEFAULT_JSON = ROOT / "reports" / "ekp_chronological_evaluation.json"
DEFAULT_MD = ROOT / "reports" / "ekp_chronological_evaluation.md"
FROZEN_ARTIFACTS = {
    "existing_production_ekp_frozen": (
        ROOT / "models" / "ekp_model.joblib",
        "aae0a3538e0c57dff7fc12bc8d20961f4802644b2f4a4cde40eb49d375e9b802",
        "production",
    ),
    "synthetic_research_candidate_frozen": (
        ROOT / "models" / "candidates" / "ekp_gradient_boosting_huber_engineered_20261024.joblib",
        "4f789db97a1c8f34537514d2baedd11f3a016c75a7f89b5026318f251740ec2e",
        "synthetic_candidate",
    ),
}


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.casefold() == ".csv":
        frame = pd.read_csv(path, dtype=object, keep_default_na=False)
    elif path.suffix.casefold() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(path, sheet_name="Production_Batches", dtype=object, keep_default_na=False)
    else:
        raise ValueError("Input must be CSV or XLSX")
    return [
        {key: (None if value == "" else value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def chronological_splits(
    records: list[Mapping[str, Any]], *, min_train_batches: int = 50,
    test_timestamps: int = 20, n_splits: int = 3,
) -> list[tuple[list[int], list[int]]]:
    """Expanding-window splits over distinct timestamp groups; no batch/timestamp crosses."""
    if min_train_batches < 2 or test_timestamps < 1 or n_splits < 1:
        raise ValueError("Split sizes must be positive; min_train_batches must be >= 2")
    ids = [str(record.get("batch_id", "")).strip() for record in records]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Chronological evaluation requires non-empty unique batch IDs")
    parsed = []
    for index, record in enumerate(records):
        try:
            stamp = datetime.fromisoformat(str(record["production_started_at"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("All production start timestamps must be ISO-8601 with timezone") from None
        parsed.append((index, stamp))
    timestamps = sorted({stamp for _, stamp in parsed})
    required = test_timestamps * n_splits
    if len(timestamps) < required + 1:
        raise ValueError(f"Insufficient distinct production timestamps: need at least {required + 1}, got {len(timestamps)}")
    splits = []
    for fold in range(n_splits):
        test_end = len(timestamps) - test_timestamps * (n_splits - fold - 1)
        test_start = test_end - test_timestamps
        train_cut = timestamps[test_start - 1]
        test_values = set(timestamps[test_start:test_end])
        train_indices = [i for i, stamp in parsed if stamp <= train_cut]
        test_indices = [i for i, stamp in parsed if stamp in test_values]
        if len(train_indices) < min_train_batches:
            raise ValueError(f"Fold {fold + 1} has only {len(train_indices)} training batches; need {min_train_batches}")
        if not train_indices or not test_indices or max(parsed[i][1] for i in train_indices) >= min(test_values):
            raise ValueError("Chronological split does not maintain strict train-before-test ordering")
        splits.append((train_indices, test_indices))
    return splits


def _metrics(y_true: list[float], y_pred: list[float], *, severe_threshold: float | None) -> dict[str, Any]:
    truth = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    if not np.isfinite(truth).all() or not np.isfinite(pred).all():
        raise ValueError("Metrics require finite actuals and predictions")
    abs_error = np.abs(pred - truth)
    return {
        "n": int(len(truth)),
        "mae_tl_kg": float(mean_absolute_error(truth, pred)),
        "rmse_tl_kg": float(math.sqrt(mean_squared_error(truth, pred))),
        "r2": float(r2_score(truth, pred)) if len(truth) >= 2 else None,
        "mean_signed_error_tl_kg_prediction_minus_actual": float(np.mean(pred - truth)),
        "absolute_error_p50_tl_kg": float(np.quantile(abs_error, 0.50)),
        "absolute_error_p90_tl_kg": float(np.quantile(abs_error, 0.90)),
        "severe_error_threshold_tl_kg": severe_threshold,
        "severe_error_rate": (
            float(np.mean(abs_error > severe_threshold)) if severe_threshold is not None else None
        ),
    }


def _score_slices(values: list[float], threshold: float | None) -> dict[str, Any]:
    truth, pred = [], []
    for actual, estimate in values:
        truth.append(actual)
        pred.append(estimate)
    return _metrics(truth, pred, severe_threshold=threshold)


def _component_metrics(y_true: list[float], y_pred: list[float], unit: str) -> dict[str, Any]:
    truth = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    if not np.isfinite(truth).all() or not np.isfinite(pred).all():
        raise ValueError("Component metrics require finite values")
    error = np.abs(pred - truth)
    return {
        "n": int(len(truth)),
        f"mae_{unit}": float(mean_absolute_error(truth, pred)),
        f"rmse_{unit}": float(math.sqrt(mean_squared_error(truth, pred))),
        "r2": float(r2_score(truth, pred)) if len(truth) >= 2 else None,
        f"mean_signed_error_{unit}_prediction_minus_actual": float(np.mean(pred - truth)),
        f"absolute_error_p50_{unit}": float(np.quantile(error, 0.50)),
        f"absolute_error_p90_{unit}": float(np.quantile(error, 0.90)),
    }


def _as_decimal(value: Any):
    from decimal import Decimal
    return Decimal(str(value))


def _eligible_dataset(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validation = validate_records(records)
    if not records:
        return [], {"status": "no_real_data", "validation": validation}
    source_types = {str(record.get("source_type", "")).strip() for record in records}
    if source_types != {"real"}:
        return [], {
            "status": "blocked_non_real_or_mixed_source",
            "validation": validation,
            "source_types_present": sorted(source_types),
        }
    bad = [item for item in validation["records"] if not item["is_valid"]]
    not_approved = [
        item["batch_id"] for item, record in zip(validation["records"], records)
        if item["is_valid"] and record.get("validation_status") != "validated"
    ]
    if bad or not_approved:
        return [], {
            "status": "blocked_data_quality",
            "validation": validation,
            "unvalidated_batch_ids": not_approved,
        }
    missing_availability_time = [
        str(record.get("batch_id"))
        for record in records
        if not record.get("record_created_at") or not record.get("validated_at")
    ]
    if missing_availability_time:
        return [], {
            "status": "blocked_outcome_availability_time",
            "validation": validation,
            "batch_ids_missing_record_or_validation_time": missing_availability_time,
        }
    ready = []
    for index, record in enumerate(records):
        try:
            features = model1_scenario_a_features(record)
            target = calculate_ekp(
                record["total_cost_tl"], record["net_output_kg"],
                currency=record["currency"], cost_period=record["cost_period"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            return [], {
                "status": "blocked_feature_or_formula",
                "validation": validation,
                "blocked_row": index + 2,
                "reason": str(exc),
            }
        if not math.isfinite(float(target)) or float(target) <= 0:
            return [], {
                "status": "blocked_invalid_target",
                "validation": validation,
                "blocked_row": index + 2,
            }
        ready.append({
            "source": record, "features": features, "target": float(target),
            "cost": float(_as_decimal(record["total_cost_tl"])),
            "yield_kg": float(_as_decimal(record["net_output_kg"])),
            "timestamp": record["production_started_at"],
        })
    return ready, {"status": "ready", "validation": validation}




def _load_hash_pinned_artifacts(feature_columns: list[str]):
    """Deserialize only the exact locally reviewed files, after hashing bytes in memory."""
    bundles = {}
    status = {}
    import joblib

    for name, (path, expected_hash, artifact_kind) in FROZEN_ARTIFACTS.items():
        item = {"path": str(path.relative_to(ROOT)), "expected_sha256": expected_hash}
        if not path.is_file():
            item["status"] = "missing"
            status[name] = item
            continue
        content = path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        item["actual_sha256"] = actual_hash
        if actual_hash != expected_hash:
            item["status"] = "hash_mismatch_not_loaded"
            status[name] = item
            continue
        try:
            package = joblib.load(io.BytesIO(content))
            model = package.get("model") if isinstance(package, dict) else package
            declared = package.get("feature_columns") if isinstance(package, dict) else getattr(model, "feature_names_in_", None)
            if declared is not None and list(declared) != feature_columns:
                raise ValueError("feature contract mismatch")
            if artifact_kind == "synthetic_candidate" and (
                not isinstance(package, dict)
                or package.get("data_type") != "synthetic"
                or package.get("production_ready") is not False
            ):
                raise ValueError("candidate metadata is not explicitly synthetic and non-production")
            if not hasattr(model, "predict"):
                raise ValueError("predict method is missing")
            bundles[name] = model
            item["status"] = "loaded_hash_pinned_diagnostic_only"
            item["production_ready"] = False
        except Exception as exc:
            item["status"] = "rejected"
            item["reason"] = str(exc)
        status[name] = item
    return bundles, status


def evaluate_records(
    records: list[dict[str, Any]], *, min_train_batches: int = 50,
    test_timestamps: int = 20, n_splits: int = 3,
    severe_error_threshold_tl_kg: float | None = None,
) -> dict[str, Any]:
    """Evaluate only validated real rows; synthetic fixtures never produce model metrics."""
    if severe_error_threshold_tl_kg is not None and (
        not math.isfinite(severe_error_threshold_tl_kg) or severe_error_threshold_tl_kg <= 0
    ):
        raise ValueError("Severe-error threshold must be a finite positive business-approved value")
    eligible, gate = _eligible_dataset(records)
    base = {
        "evaluation_type": "chronological_expanding_window",
        "target": "total_cost_tl / measured net_output_kg; TRY/kg",
        "data_type": "real production records only",
        "source_type_separation": "synthetic and external benchmark rows are rejected, not mixed",
        "production_before_features": list(MODEL1_FEATURE_MAP),
        "excluded_target_or_postproduction_fields": [
            "net_output_kg", "total_cost_tl", "cost components", "observed losses",
            "drying_loss_pct", "sorting_loss_pct", "labor_hours", "energy_kwh",
        ],
        "feature_availability_gate": "all model features must come from planned_* fields and a timezone-aware plan_snapshot_at <= production_started_at",
        "outcome_availability_gate": "record_created_at and validated_at are required; training labels must have been created and validated by the first test production timestamp",
        "candidate_policy": "Incumbent Random Forest and the engineered GradientBoosting-Huber research-candidate architecture are refit only on each historical training window with fixed parameters; preprocessing is fit inside each window. Frozen production and synthetic research artifacts are additionally scored only when their bytes match pinned SHA-256 values; the synthetic artifact remains a diagnostic, not a production candidate.",
        "approach_definitions": {
            "direct_ekp": "Fit a direct EKP target model from production-before plan features.",
            "predicted_cost_over_predicted_net_output": "Fit separate total-cost and net-output models on historical training batches; divide their test predictions. Actual test cost/output are evaluation targets only.",
            "hybrid_known_cost_plus_predicted_residual": "Compute planned meat, tail-fat, spice, casing, and Fason service subtotal; fit remaining cost residual and net-output models on historical batches. Factory accounting scope must be confirmed.",
        },
        "split_policy": {
            "min_train_batches": min_train_batches,
            "test_distinct_timestamps_per_window": test_timestamps,
            "windows": n_splits,
            "test_windows_disjoint": True,
        },
        "severe_error_threshold_tl_kg": severe_error_threshold_tl_kg,
        "component_metric_units": {"predicted_total_cost_rf": "TL/batch", "predicted_total_cost_hybrid": "TL/batch", "predicted_net_output_rf": "kg"},
        "status": gate["status"],
        "frozen_artifact_evaluation": "not_run_until_validated_real_rows_exist",
        "validation_summary": {k: v for k, v in gate.get("validation", {}).items() if k != "records"},
    }
    if "source_types_present" in gate:
        base["source_types_present"] = gate["source_types_present"]
    if "unvalidated_batch_ids" in gate:
        base["unvalidated_batch_ids"] = gate["unvalidated_batch_ids"]
    if "batch_ids_missing_record_or_validation_time" in gate:
        base["batch_ids_missing_record_or_validation_time"] = gate["batch_ids_missing_record_or_validation_time"]
    if "blocked_row" in gate:
        base["blocked_row"] = gate["blocked_row"]
        base["reason"] = gate["reason"]
    if not eligible:
        base.update({"metrics": {}, "folds": [], "group_metrics": {}, "limitations": [
            "No real-factory performance is measured unless status=complete and eligible chronological windows exist.",
            "A template with no rows is expected before factory data is supplied; no synthetic fallback is used.",
            "Direct EKP, cost/output ratio, and hybrid methods are defined for future comparison but no real-data score exists yet.",
            "Pinned SHA-256 values detect unexpected local artifact changes; they do not prove who created an artifact or that its model is scientifically valid.",
        ]})
        return base

    from training.compare_ekp_models import FEATURES, pipe, known_subtotal
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

    try:
        splits = chronological_splits(
            [item["source"] for item in eligible],
            min_train_batches=min_train_batches,
            test_timestamps=test_timestamps,
            n_splits=n_splits,
        )
        safe_splits = []
        for train_indices, test_indices in splits:
            test_start = min(eligible[i]["timestamp"] for i in test_indices)
            available_train = [
                i for i in train_indices
                if datetime.fromisoformat(str(eligible[i]["source"]["record_created_at"]).replace("Z", "+00:00")) <= test_start
                and datetime.fromisoformat(str(eligible[i]["source"]["validated_at"]).replace("Z", "+00:00")) <= test_start
            ]
            if len(available_train) < min_train_batches:
                raise ValueError(
                    f"Only {len(available_train)} prior batches had recorded/validated outcomes by test start {test_start}; need {min_train_batches}"
                )
            safe_splits.append((available_train, test_indices))
        splits = safe_splits
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        base.update({
            "status": "blocked_insufficient_chronological_data",
            "reason": str(exc),
            "metrics": {},
            "folds": [],
            "group_metrics": {},
            "limitations": ["No metric was produced because chronological training/test and outcome-availability constraints were not satisfied."],
        })
        return base
    x = pd.DataFrame([item["features"] for item in eligible], columns=FEATURES)
    y = np.asarray([item["target"] for item in eligible], dtype=float)
    actual_cost = np.asarray([item["cost"] for item in eligible], dtype=float)
    actual_yield = np.asarray([item["yield_kg"] for item in eligible], dtype=float)
    known_cost = np.asarray(known_subtotal(x), dtype=float)
    if not np.isfinite(known_cost).all() or np.any(known_cost < 0):
        raise ValueError("Planned known-cost formula returned invalid values")
    candidate_estimators = {
        "random_forest_refit": pipe(RandomForestRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=-1,
        )),
        "gradient_boosting_huber_engineered_refit": pipe(
            GradientBoostingRegressor(
                loss="huber", n_estimators=160, learning_rate=0.03,
                max_depth=2, min_samples_leaf=5, random_state=42,
            ),
            engineered=True,
        ),
    }
    frozen_models, frozen_status = _load_hash_pinned_artifacts(FEATURES)
    ratio_models = {
        "predicted_total_cost_over_predicted_net_output_rf",
        "planned_known_cost_plus_predicted_residual_over_predicted_net_output_rf",
    }
    by_model: dict[str, list[tuple[float, float]]] = {
        "training_mean_baseline": [], "training_median_baseline": [],
        **{name: [] for name in candidate_estimators},
        **{name: [] for name in frozen_models},
        **{name: [] for name in ratio_models},
    }
    component_predictions = {
        "predicted_total_cost_rf": [],
        "predicted_total_cost_hybrid": [],
        "predicted_net_output_rf": [],
    }
    fold_results = []
    test_prediction_rows = []
    for fold_number, (train_i, test_i) in enumerate(splits, start=1):
        y_train, y_test = y[train_i], y[test_i]
        predictions: dict[str, np.ndarray] = {
            "training_mean_baseline": np.full(len(test_i), float(np.mean(y_train))),
            "training_median_baseline": np.full(len(test_i), float(np.median(y_train))),
        }
        for name, estimator in candidate_estimators.items():
            fitted = estimator.fit(x.iloc[train_i], y_train)
            values = np.asarray(fitted.predict(x.iloc[test_i]), dtype=float)
            if not np.isfinite(values).all() or np.any(values <= 0):
                raise ValueError(f"{name} returned non-finite or non-positive EKP predictions")
            predictions[name] = values
        for name, model in frozen_models.items():
            values = np.asarray(model.predict(x.iloc[test_i]), dtype=float)
            if not np.isfinite(values).all() or np.any(values <= 0):
                raise ValueError(f"{name} returned non-finite or non-positive EKP predictions")
            predictions[name] = values

        rf_cost = pipe(RandomForestRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=-1,
        )).fit(x.iloc[train_i], actual_cost[train_i])
        rf_yield = pipe(RandomForestRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=-1,
        )).fit(x.iloc[train_i], actual_yield[train_i])
        predicted_cost = np.asarray(rf_cost.predict(x.iloc[test_i]), dtype=float)
        predicted_yield = np.asarray(rf_yield.predict(x.iloc[test_i]), dtype=float)
        residual_rf = pipe(RandomForestRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=-1,
        ), engineered=True).fit(
            x.iloc[train_i], actual_cost[train_i] - known_cost[train_i]
        )
        predicted_residual = np.asarray(residual_rf.predict(x.iloc[test_i]), dtype=float)
        hybrid_cost = known_cost[test_i] + predicted_residual
        component_predictions["predicted_total_cost_rf"].extend(zip(actual_cost[test_i], predicted_cost))
        component_predictions["predicted_total_cost_hybrid"].extend(zip(actual_cost[test_i], hybrid_cost))
        component_predictions["predicted_net_output_rf"].extend(zip(actual_yield[test_i], predicted_yield))
        if (np.any(predicted_cost <= 0) or np.any(predicted_yield <= 0)
                or not np.isfinite(predicted_cost).all() or not np.isfinite(predicted_yield).all()):
            raise ValueError("Cost/yield ratio approach produced non-finite or non-positive cost/output")
        if (np.any(hybrid_cost <= 0) or not np.isfinite(hybrid_cost).all()):
            raise ValueError("Hybrid approach produced non-finite or non-positive total cost")
        predictions["predicted_total_cost_over_predicted_net_output_rf"] = predicted_cost / predicted_yield
        predictions["planned_known_cost_plus_predicted_residual_over_predicted_net_output_rf"] = hybrid_cost / predicted_yield
        fold_metric = {}
        for name, values in predictions.items():
            pairs = list(zip(y_test.tolist(), values.tolist()))
            by_model[name].extend(pairs)
            fold_metric[name] = _metrics(
                y_test.tolist(), values.tolist(),
                severe_threshold=severe_error_threshold_tl_kg,
            )
        for position, row_index in enumerate(test_i):
            test_prediction_rows.append({
                "index": row_index,
                "actual": float(y_test[position]),
                "predictions": {name: float(values[position]) for name, values in predictions.items()},
            })
        fold_results.append({
            "fold": fold_number,
            "train_n": len(train_i),
            "test_n": len(test_i),
            "train_end": max(eligible[i]["timestamp"] for i in train_i),
            "test_start": min(eligible[i]["timestamp"] for i in test_i),
            "test_end": max(eligible[i]["timestamp"] for i in test_i),
            "metrics": fold_metric,
        })
    metrics = {name: _score_slices(values, severe_error_threshold_tl_kg) for name, values in by_model.items()}
    component_units = {
        "predicted_total_cost_rf": "tl_batch",
        "predicted_total_cost_hybrid": "tl_batch",
        "predicted_net_output_rf": "kg",
    }
    component_metrics = {
        name: _component_metrics(
            [float(pair[0]) for pair in pairs],
            [float(pair[1]) for pair in pairs],
            unit=component_units[name],
        )
        for name, pairs in component_predictions.items()
    }
    median_mae = metrics["training_median_baseline"]["mae_tl_kg"]
    for values in metrics.values():
        values["improvement_vs_median_baseline_pct"] = (
            100.0 * (median_mae - values["mae_tl_kg"]) / median_mae if median_mae else None
        )

    group_metrics = {}
    min_group_size = 10
    for group_name, model_field in (
        ("region", "Bolge"),
        ("recipe_profile", "Recete_profili"),
        ("process_method", "Isleme_modeli"),
    ):
        group_metrics[group_name] = {}
        for model_name in metrics:
            grouped: dict[str, list[tuple[float, float]]] = {}
            for evaluated in test_prediction_rows:
                category = str(eligible[evaluated["index"]]["features"][model_field])
                pair = (evaluated["actual"], evaluated["predictions"][model_name])
                grouped.setdefault(category, []).append(pair)
            group_metrics[group_name][model_name] = {
                category: (
                    _score_slices(pairs, severe_error_threshold_tl_kg)
                    if len(pairs) >= min_group_size else
                    {"n": len(pairs), "status": "not_scored_insufficient_group_size", "minimum_n": min_group_size}
                )
                for category, pairs in grouped.items()
            }
    base.update({
        "status": "complete",
        "frozen_artifact_evaluation": frozen_status,
        "real_batches": len(eligible),
        "first_production_start": min(item["timestamp"] for item in eligible),
        "last_production_start": max(item["timestamp"] for item in eligible),
        "features": FEATURES,
        "metrics": metrics,
        "component_metrics": component_metrics,
        "approach_comparison": {
            "direct_ekp": ["random_forest_refit", "gradient_boosting_huber_engineered_refit", "existing_production_ekp_frozen", "synthetic_research_candidate_frozen"],
            "predicted_total_cost_over_predicted_net_output": {
                "ekp_metric": "predicted_total_cost_over_predicted_net_output_rf",
                "component_metrics": ["predicted_total_cost_rf", "predicted_net_output_rf"],
                "realized_cost_and_output_used_as_training_targets_only": True,
            },
            "known_planned_cost_plus_predicted_residual_over_predicted_net_output": {
                "ekp_metric": "planned_known_cost_plus_predicted_residual_over_predicted_net_output_rf",
                "known_cost_formula": "planned meat + tail fat + spices + casing; planned fason service only when process_method=Fason",
                "remaining_cost_and_yield_models_fit_on_training_window_only": True,
                "known_cost_availability_and_accounting_match_require_factory_owner_confirmation": True,
            },
        },
        "folds": fold_results,
        "group_metrics": group_metrics,
        "models": list(metrics),
        "same_test_batches_across_models": True,
        "group_minimum_n": min_group_size,
        "limitations": [
            "These metrics apply only to the supplied, source-validated real batches and selected chronological windows.",
            "They are not external site validation and do not establish production readiness.",
            "Frozen artifact scores are cross-domain diagnostics; a SHA-256 match protects bytes, not source authenticity or scientific validity.",
            "Synthetic-only research candidate metrics must not be presented as real training evidence or promoted to production.",
            "Serious-error rate is not interpreted unless a business-approved threshold is supplied.",
            "Preproduction availability is asserted by recorded plan snapshots and still requires data-owner audit.",
        ],
    })
    return base


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Gerçek veriyle kronolojik EKP değerlendirmesi", "",
        f"- Durum: **{report['status']}**",
        f"- Kaynak türü: {report['data_type']}",
        f"- Değerlendirme: {report['evaluation_type']}",
        f"- Hedef: {report['target']}",
        "",
    ]
    if report["status"] == "no_real_data":
        lines += [
            "Gerçek üretim kaydı bulunmadı. Girdi, başlıkları olan boş veri şablonudur.",
            "Model metriği hesaplanmadı; sentetik veriden zaman bazlı gerçek performans üretilmedi.",
        ]
    elif report["status"] == "complete":
        lines += [
            f"Değerlendirilen gerçek parti: {report['real_batches']}",
            f"Dönem: {report['first_production_start']} — {report['last_production_start']}",
            "",
            "| Model | n | MAE TL/kg | RMSE TL/kg | R² | Medyan baseline'a göre MAE iyileşmesi |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for name, metric in report["metrics"].items():
            improvement = metric["improvement_vs_median_baseline_pct"]
            lines.append(f"| {name} | {metric['n']} | {metric['mae_tl_kg']:.4f} | {metric['rmse_tl_kg']:.4f} | {metric['r2'] if metric['r2'] is not None else 'n/a'} | {improvement if improvement is not None else 'n/a'} |")
    else:
        lines.append("Değerlendirme veri kalite/kaynak/zaman/özellik koşullarını sağlamadığı için durduruldu.")
        lines.append(f"Doğrulama özeti: {json.dumps(report.get('validation_summary', {}), ensure_ascii=False)}")
        if "reason" in report:
            lines.append(f"Engel: {report['reason']}")
    lines += [
        "",
        "## Yöntem ve sınırlamalar", "",
        f"- Eğitim minimumu: {report['split_policy']['min_train_batches']} batch; pencere başına {report['split_policy']['test_distinct_timestamps_per_window']} farklı üretim zaman damgası; {report['split_policy']['windows']} genişleyen pencere.",
        "- Eğitim hedefleri, her test penceresinin başlangıcında hem kaydedilmiş hem de onaylanmış olmalıdır; sonradan backfill edilen hedefler o fold'un eğitiminden çıkarılır.",
        "- Fark = tahmin − gerçekleşen; pozitif işaret fazla tahmini gösterir.",
        "- Yalnız gerçek, onaylı kayıtlar kullanılır; sentetik/benchmark kayıtlar karıştırılmaz.",
        "- Planlanan girdiler ve fiyatlar ancak timestamp'li, üretim öncesi snapshot ile özellik olur.",
        "- Net çıktı, toplam/gerçekleşen maliyet, gerçekleşmiş kayıplar, gerçekleşen enerji ve işçilik model girdilerinden çıkarılır.",
        "- Tahmini maliyet/tahmini net çıktı yönteminde iki alt model yalnız geçmiş eğitim penceresiyle fit edilir; gerçekleşen test maliyet/çıktısı yalnız hedef/ölçüm içindir.",
        "- Hibrit maliyet formülündeki bilinen alt toplam yalnız plan miktarı/fiyatı ve fason oranından türetilir; muhasebe kapsamının gerçek süreçle eşleşmesi doğrulanmalıdır.",
        "- Ciddi hata oranı ancak iş sahibi TL/kg eşiği verirse hesaplanır.",
        "- Maliyet/yield ve hibrit yaklaşımlarında gerçekleşen test maliyeti/çıktı özellik olarak kullanılmaz.",
        "- Hash kontrolü pickle dosyası içeriğinin sabitlenmiş yerel baytlarla aynı olduğunu gösterir; dijital imza, güvenilir kaynak veya bilimsel doğrulama değildir.",
        "- Veri doğrulama ve satır/alan sorunları JSON raporundadır; hatalı kayıtlar silinmez/düzeltilmez.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--min-train-batches", type=int, default=50)
    parser.add_argument("--test-timestamps", type=int, default=20)
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--severe-error-threshold-tl-kg", type=float)
    args = parser.parse_args()
    records = read_records(args.input)
    report = evaluate_records(
        records,
        min_train_batches=args.min_train_batches,
        test_timestamps=args.test_timestamps,
        n_splits=args.splits,
        severe_error_threshold_tl_kg=args.severe_error_threshold_tl_kg,
    )
    report["input_path"] = str(args.input.resolve())
    write_report(report, args.json_output, args.markdown_output)
    print(json.dumps({
        "status": report["status"],
        "input_rows": report.get("validation_summary", {}).get("rows", 0),
        "metrics": report.get("metrics", {}),
        "json_report": str(args.json_output.resolve()),
        "markdown_report": str(args.markdown_output.resolve()),
    }, ensure_ascii=False, indent=2))
    return 2 if report["status"].startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
