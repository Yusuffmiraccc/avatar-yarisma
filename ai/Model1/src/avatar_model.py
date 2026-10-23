"""Train/evaluate the AVATAR-specific production-output model on validated actual records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
TARGET = "actual_package_count"
NUMERIC_FEATURES = [
    "meat_kg",
    "spice_kg",
    "casing_kg",
    "package_weight_kg",
    "planned_material_cost_eur",
    "planned_service_cost_eur",
]
CATEGORICAL_FEATURES = ["recipe_variant"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
REQUIRED_COLUMNS = {
    "production_order_id", "production_date", "recipe_variant", "meat_kg", "spice_kg",
    "casing_kg", "package_weight_kg", "planned_material_cost_eur", "planned_service_cost_eur",
    "actual_package_count",
}


class TrainingDataError(ValueError):
    """Raised when actual production records cannot safely be used for training."""


def prepare_training_frame(records: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS - set(records.columns))
    if missing:
        raise TrainingDataError(f"Eğitim kayıtlarında zorunlu alanlar eksik: {missing}")
    df = records.copy()
    if df["production_order_id"].isna().any() or df["production_order_id"].duplicated().any():
        raise TrainingDataError("production_order_id boş olamaz ve her üretim emri benzersiz olmalıdır.")
    df["production_date"] = pd.to_datetime(df["production_date"], errors="coerce")
    for col in NUMERIC_FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["recipe_variant"] = df["recipe_variant"].fillna("Unknown").astype(str)
    df = df.dropna(subset=["production_date", *NUMERIC_FEATURES, TARGET]).copy()
    positive_cols = ["meat_kg", "package_weight_kg", TARGET]
    if (df[positive_cols] <= 0).any().any():
        raise TrainingDataError("Et miktarı, paket ağırlığı ve gerçek paket sayısı sıfırdan büyük olmalıdır.")
    nonnegative_cols = ["spice_kg", "casing_kg", "planned_material_cost_eur", "planned_service_cost_eur"]
    if (df[nonnegative_cols] < 0).any().any():
        raise TrainingDataError("Miktarlar ve planlanan maliyetler negatif olamaz.")
    df = df.sort_values(["production_date", "production_order_id"]).reset_index(drop=True)
    if len(df) < 100:
        raise TrainingDataError(f"İlk eğitim için en az 100 doğrulanmış gerçek üretim kaydı gerekli; kullanılabilir kayıt: {len(df)}.")
    return df


def _preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("num", numeric, NUMERIC_FEATURES),
        ("cat", categorical, CATEGORICAL_FEATURES),
    ])


def _pipeline(algorithm: str) -> Pipeline:
    if algorithm == "linear_regression":
        estimator = LinearRegression()
    elif algorithm == "random_forest":
        estimator = RandomForestRegressor(
            n_estimators=300, min_samples_leaf=4, max_features=0.9,
            random_state=42, n_jobs=-1,
        )
    else:
        raise ValueError(f"Bilinmeyen algoritma: {algorithm}")
    return Pipeline([("preprocess", _preprocessor()), ("model", estimator)])


def _metric_pack(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    pred = np.maximum(np.asarray(y_pred, dtype=float), 0.0)
    return {
        "mae_packages": round(float(mean_absolute_error(y_true, pred)), 4),
        "rmse_packages": round(float(np.sqrt(mean_squared_error(y_true, pred))), 4),
        "r2": round(float(r2_score(y_true, pred)), 4) if len(y_true) > 1 else 0.0,
    }


def naive_baseline(df: pd.DataFrame) -> np.ndarray:
    """Reference forecast: input meat kg / nominal package weight kg."""
    return (df["meat_kg"].to_numpy(dtype=float) / df["package_weight_kg"].to_numpy(dtype=float))


@dataclass
class TrainingResult:
    promoted: bool
    reason: str
    algorithm: str | None
    metrics: dict[str, Any]
    model_bundle: dict[str, Any] | None
    model_version: str | None


def train_candidate(
    records: pd.DataFrame,
    *,
    incumbent_bundle: dict[str, Any] | None = None,
) -> TrainingResult:
    """Evaluate time-ordered holdout and produce a deployable candidate only if better.

    Candidate models are compared on the newest 20% of records. A candidate must beat
    the physical-reference baseline and, where available, the incumbent model on that
    exact holdout. Accepted candidates are then refit on all eligible records.
    """
    df = prepare_training_frame(records)
    split_at = int(np.floor(len(df) * 0.8))
    if split_at < 50 or len(df) - split_at < 20:
        raise TrainingDataError("Zaman sıralı değerlendirme için en az 50 eğitim ve 20 test kaydı gerekli.")
    train = df.iloc[:split_at].copy()
    test = df.iloc[split_at:].copy()
    x_train, y_train = train[FEATURES], train[TARGET]
    x_test, y_test = test[FEATURES], test[TARGET]

    baseline_metrics = _metric_pack(y_test, naive_baseline(test))
    algorithm_metrics: dict[str, dict[str, float]] = {}
    fitted_candidates: dict[str, Pipeline] = {}
    for algorithm in ("linear_regression", "random_forest"):
        model = _pipeline(algorithm)
        model.fit(x_train, y_train)
        prediction = np.maximum(model.predict(x_test), 0.0)
        algorithm_metrics[algorithm] = _metric_pack(y_test, prediction)
        fitted_candidates[algorithm] = model

    best_algorithm = min(algorithm_metrics, key=lambda name: algorithm_metrics[name]["mae_packages"])
    best_metrics = algorithm_metrics[best_algorithm]
    incumbent_metrics: dict[str, float] | None = None
    if incumbent_bundle is not None:
        incumbent_model = incumbent_bundle.get("model")
        incumbent_features = incumbent_bundle.get("feature_columns", FEATURES)
        if incumbent_model is not None and list(incumbent_features) == FEATURES:
            incumbent_pred = np.maximum(incumbent_model.predict(x_test[FEATURES]), 0.0)
            incumbent_metrics = _metric_pack(y_test, incumbent_pred)

    beats_baseline = best_metrics["mae_packages"] < baseline_metrics["mae_packages"]
    beats_incumbent = incumbent_metrics is None or best_metrics["mae_packages"] < incumbent_metrics["mae_packages"]
    metrics: dict[str, Any] = {
        "dataset_type": "actual_validated_avatar_production_records",
        "target": TARGET,
        "eligible_records": int(len(df)),
        "train_records_for_validation": int(len(train)),
        "test_records": int(len(test)),
        "train_date_range": [str(train["production_date"].min().date()), str(train["production_date"].max().date())],
        "test_date_range": [str(test["production_date"].min().date()), str(test["production_date"].max().date())],
        "baseline_meat_mass": baseline_metrics,
        "linear_regression": algorithm_metrics["linear_regression"],
        "random_forest": algorithm_metrics["random_forest"],
        "selected_algorithm": best_algorithm,
        "selected_candidate": best_metrics,
        "incumbent_on_same_holdout": incumbent_metrics,
        "candidate_beats_baseline": beats_baseline,
        "candidate_beats_incumbent": beats_incumbent,
        "interpretation_warning": "Son test dilimi, zaman sıralı holdout'tur. En az 100 kayıt eşiği iş kuralıdır; tek başına genellenebilirliği garanti etmez.",
    }
    if not beats_baseline:
        return TrainingResult(False, "Candidate, basit et-kütlesi baseline yönteminden daha düşük MAE elde etmedi; mevcut model varsa korundu.", best_algorithm, metrics, None, None)
    if not beats_incumbent:
        return TrainingResult(False, "Candidate, aynı test dilimindeki aktif modelden daha düşük MAE elde etmedi; aktif model korundu.", best_algorithm, metrics, None, None)

    # Refit chosen algorithm on all eligible actual records after the holdout check.
    final_model = _pipeline(best_algorithm)
    final_model.fit(df[FEATURES], df[TARGET])
    version = datetime.now(timezone.utc).strftime("v%Y%m%dT%H%M%S%fZ")
    bundle = {
        "model": final_model,
        "feature_columns": FEATURES,
        "target": TARGET,
        "model_version": version,
        "algorithm": best_algorithm,
        "trained_records": int(len(df)),
        "trained_through_date": str(df["production_date"].max().date()),
        "model_domain": "AVATAR actual production records; only validated completed production orders",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return TrainingResult(True, "Candidate doğrulama koşullarını geçti; aktif model olarak yayınlanmaya hazır.", best_algorithm, metrics, bundle, version)


def save_candidate(bundle: dict[str, Any], artifact_dir: Path = ROOT / "models") -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    version = str(bundle["model_version"])
    path = artifact_dir / f"avatar_production_quantity_model_{version}.joblib"
    joblib.dump(bundle, path)
    return path
