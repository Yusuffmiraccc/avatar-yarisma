"""Train and evaluate synthetic Model B candidates without claiming field performance.

Run from the repository's ``ai`` directory:
    python -m Model2.training.train_model_b
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "splits"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports" / "synthetic_evaluation"
FEATURES = ["hayvan_turu", "karkas_agirligi_kg"]
TARGETS = [
    "but_kg", "sirt_kg", "omuz_kg", "kaburga_kg", "kiyma_kg",
    "yan_urun_kg", "kemik_yag_sinir_kg", "fire_kg",
]
SEED = 20261024
DATA_VERSION = "model-b-synthetic-v1"


def load_splits() -> tuple[dict[str, pd.DataFrame], str]:
    paths = {
        "train": DATA_DIR / "ModelB_train_sentetik.csv",
        "validation": DATA_DIR / "ModelB_validation_sentetik.csv",
        "test": DATA_DIR / "ModelB_test_sentetik.csv",
    }
    splits = {name: pd.read_csv(path) for name, path in paths.items()}
    required = {
        "kayit_id", *FEATURES, *TARGETS, "veri_kaynagi", "bolum",
        "toplam_cikis_kg", "agirlik_dengesi_farki_kg",
    }
    for name, frame in splits.items():
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name}: eksik sütunlar: {sorted(missing)}")
        if not frame["veri_kaynagi"].eq("SENTETIK_SIMULASYON").all():
            raise ValueError(f"{name}: sentetik olmayan/etiketsiz kayıt bulundu")
        if not frame["bolum"].eq(name).all():
            raise ValueError(f"{name}: bolum etiketi dosya adıyla uyuşmuyor")
        if not frame["hayvan_turu"].isin({"kuzu", "koyun", "dana"}).all():
            raise ValueError(f"{name}: bilinmeyen hayvan türü bulundu")
        if frame["kayit_id"].duplicated().any():
            raise ValueError(f"{name}: yinelenen kayit_id bulundu")
        numeric = frame[["karkas_agirligi_kg", *TARGETS, "toplam_cikis_kg", "agirlik_dengesi_farki_kg"]].to_numpy(dtype=float)
        # The signed balance residual is not an output weight and may be negative.
        weights, residual = numeric[:, :-1], numeric[:, -1]
        if not np.isfinite(weights).all() or (weights < 0).any() or not np.isfinite(residual).all():
            raise ValueError(f"{name}: negatif veya sonlu olmayan ağırlık bulundu")
        if (frame["karkas_agirligi_kg"] <= 0).any():
            raise ValueError(f"{name}: karkas ağırlığı sıfır/negatif olamaz")
        target_sum = frame[TARGETS].sum(axis=1).to_numpy(dtype=float)
        if not np.allclose(target_sum, frame["toplam_cikis_kg"], atol=0.01, rtol=0):
            raise ValueError(f"{name}: sentetik toplam_cikis_kg formülü tutarsız")
        if not np.allclose(
            frame["toplam_cikis_kg"] - frame["karkas_agirligi_kg"],
            frame["agirlik_dengesi_farki_kg"], atol=0.01, rtol=0,
        ):
            raise ValueError(f"{name}: sentetik agirlik_dengesi_farki_kg formülü tutarsız")
    ids = {name: set(frame["kayit_id"]) for name, frame in splits.items()}
    if ids["train"] & ids["validation"] or ids["train"] & ids["test"] or ids["validation"] & ids["test"]:
        raise ValueError("Train/validation/test kayıt kimlikleri çakışıyor")
    combined = pd.concat(list(splits.values()), ignore_index=True)
    if len(combined) != 1200 or combined["kayit_id"].nunique() != len(combined):
        raise ValueError("Beklenen 1.200 benzersiz split kaydı doğrulanamadı")
    source_hash = hashlib.sha256(
        b"".join(paths[name].read_bytes() for name in ("train", "validation", "test"))
    ).hexdigest()
    return splits, source_hash


class SpeciesMeanRatio:
    """Train-only species mean target ratio baseline, scaled by carcass kg."""

    def fit(self, x: pd.DataFrame, y: pd.DataFrame) -> "SpeciesMeanRatio":
        ratios = y.div(x["karkas_agirligi_kg"].to_numpy(), axis=0)
        self.ratios_ = ratios.groupby(x["hayvan_turu"]).mean()
        self.global_ratio_ = ratios.mean(axis=0)
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        result = []
        for _, row in x.iterrows():
            ratio = self.ratios_.loc[row["hayvan_turu"]] if row["hayvan_turu"] in self.ratios_.index else self.global_ratio_
            result.append(ratio.to_numpy() * row["karkas_agirligi_kg"])
        return np.asarray(result)


def make_models() -> dict[str, Any]:
    preprocessor = ColumnTransformer(
        [
            ("species", OneHotEncoder(handle_unknown="ignore"), ["hayvan_turu"]),
            ("weight", StandardScaler(), ["karkas_agirligi_kg"]),
        ]
    )
    return {
        "baseline_species_mean_ratio": SpeciesMeanRatio(),
        "ridge": Pipeline([("preprocessor", preprocessor), ("regressor", Ridge(alpha=1.0))]),
        "random_forest": Pipeline([
            ("preprocessor", ColumnTransformer(
                [("species", OneHotEncoder(handle_unknown="ignore"), ["hayvan_turu"])],
                remainder="passthrough",
            )),
            ("regressor", RandomForestRegressor(
                n_estimators=300, min_samples_leaf=3, random_state=SEED, n_jobs=1
            )),
        ]),
    }


def score(model: Any, frame: pd.DataFrame, split_name: str, model_name: str) -> list[dict[str, Any]]:
    actual = frame[TARGETS].to_numpy(dtype=float)
    predicted = model.predict(frame[FEATURES])
    rows = []
    for i, target in enumerate(TARGETS):
        rows.append({
            "split": split_name,
            "source_type": "synthetic",
            "model": model_name,
            "target": target,
            "n": int(len(frame)),
            "mae_kg": float(mean_absolute_error(actual[:, i], predicted[:, i])),
            "rmse_kg": float(mean_squared_error(actual[:, i], predicted[:, i]) ** 0.5),
            "r2": float(r2_score(actual[:, i], predicted[:, i])) if len(frame) > 1 else None,
        })
    return rows


def normalized_validation_mae(rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> float:
    base = {row["target"]: row["mae_kg"] for row in baseline_rows}
    return float(np.mean([r["mae_kg"] / base[r["target"]] for r in rows]))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    splits, source_hash = load_splits()
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    candidates = make_models()
    for model in candidates.values():
        model.fit(train[FEATURES], train[TARGETS])

    val_rows: dict[str, list[dict[str, Any]]] = {}
    for name, model in candidates.items():
        val_rows[name] = score(model, validation, "validation", name)
    baseline_validation = val_rows["baseline_species_mean_ratio"]
    selected = min(
        ("ridge", "random_forest"),
        key=lambda name: normalized_validation_mae(val_rows[name], baseline_validation),
    )
    # Test is reported once, only after validation-based selection.
    report_rows = []
    overall_test_metrics = []
    for name, model in candidates.items():
        report_rows.extend(score(model, test, "test", name))
        actual = test[TARGETS].to_numpy(dtype=float)
        predicted = model.predict(test[FEATURES])
        overall_test_metrics.append({
            "split": "test",
            "source_type": "synthetic",
            "model": name,
            "n": int(len(test)),
            "target_count": len(TARGETS),
            "mae_kg_flattened": float(mean_absolute_error(actual.ravel(), predicted.ravel())),
            "rmse_kg_flattened": float(mean_squared_error(actual.ravel(), predicted.ravel()) ** 0.5),
            "r2_uniform_average": float(r2_score(actual, predicted, multioutput="uniform_average")),
        })
    selected_ratio = normalized_validation_mae(val_rows[selected], baseline_validation)
    readiness = "NOT_READY_SYNTHETIC_ONLY"
    bundle = {
        "model": candidates[selected],
        "feature_columns": FEATURES,
        "target_columns": TARGETS,
        "model_version": f"model-b-{selected}-{SEED}-synthetic-v1",
        "data_version": DATA_VERSION,
        "source_type": "synthetic",
        "production_ready": False,
        "selection": {"split": "validation", "selected_candidate": selected,
                      "normalized_mae_vs_baseline": selected_ratio},
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_path = MODEL_DIR / "model_b_synthetic_candidate.joblib"
    joblib.dump(bundle, candidate_path)
    candidate_manifest = {
        "manifest_version": 1,
        "artifact_filename": candidate_path.name,
        "artifact_sha256": sha256_file(candidate_path),
        "model_version": bundle["model_version"],
        "data_version": bundle["data_version"],
        "source_type": bundle["source_type"],
        "production_ready": bundle["production_ready"],
        "feature_columns": FEATURES,
        "target_columns": TARGETS,
    }
    (MODEL_DIR / "model_b_synthetic_candidate.manifest.json").write_text(
        json.dumps(candidate_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    payload = {
        "data_version": DATA_VERSION,
        "source_type": "synthetic",
        "source_sha256_combined_splits": source_hash,
        "split_counts": {name: len(df) for name, df in splits.items()},
        "split_method": "Provided stratified-by-species CSV partitions; disjoint kayit_id; random seed documented by source package as 20261024. No re-splitting.",
        "features": FEATURES,
        "targets": TARGETS,
        "validation_metrics": [row for name in ("baseline_species_mean_ratio", "ridge", "random_forest") for row in val_rows[name]],
        "selection_split": "validation",
        "selected_candidate": selected,
        "production_readiness": readiness,
        "candidate_test_metrics": report_rows,
        "overall_test_metrics": overall_test_metrics,
        "warning": "Bütün kayıtlar sentetik/simüledir; bu sonuçlar gerçek hayvan veya işletme başarısı değildir.",
    }
    (REPORT_DIR / "model_b_candidate_metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(report_rows).to_csv(REPORT_DIR / "model_b_candidate_metrics.csv", index=False)
    overall_frame = pd.DataFrame(overall_test_metrics).rename(columns={
        "model": "model", "mae_kg_flattened": "MAE_kg_tum_hedefler",
        "rmse_kg_flattened": "RMSE_kg_tum_hedefler", "r2_uniform_average": "R2_tum_hedefler",
    })
    overall_frame[["model", "MAE_kg_tum_hedefler", "RMSE_kg_tum_hedefler", "R2_tum_hedefler"]].assign(
        yorum="Sentetik test holdout; gerçek saha başarısı değildir."
    ).to_csv(REPORT_DIR / "ModelB_sentetik_model_degerlendirme.csv", index=False)
    metric_frame = pd.DataFrame(report_rows)
    baseline = metric_frame[metric_frame["model"] == "baseline_species_mean_ratio"][["target", "mae_kg"]].rename(
        columns={"mae_kg": "baseline_MAE_kg"}
    )
    forest = metric_frame[metric_frame["model"] == "random_forest"][["target", "mae_kg", "rmse_kg", "r2", "n"]].rename(
        columns={"mae_kg": "RF_MAE_kg", "rmse_kg": "RF_RMSE_kg", "r2": "RF_R2", "n": "test_n"}
    )
    baseline.merge(forest, on="target").rename(columns={"target": "hedef"})[
        ["hedef", "RF_MAE_kg", "RF_RMSE_kg", "RF_R2", "baseline_MAE_kg", "test_n"]
    ].to_csv(REPORT_DIR / "ModelB_hedef_bazli_metrikler.csv", index=False)
    print(json.dumps({"selected": selected, "production_readiness": readiness,
                      "test_rows": len(report_rows), "output": str(MODEL_DIR / "model_b_synthetic_candidate.joblib")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
