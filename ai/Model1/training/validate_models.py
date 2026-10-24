"""Leakage-aware validation; saves candidates without replacing API models."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw/sucuk_uretim_1000_simule_parti.csv"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
TARGET_YIELD = "Net_sucuk_ciktisi_kg_simule"
TARGET_EKP = "EKP_TL_kg"
TARGET_COST = "Toplam_parti_maliyeti_TL"
LOSS = ["Kuruma_kaybi_pct", "Ayiklama_fire_pct"]
NUMERIC = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg", "Kilif_metre", "Et_fiyat_TL_kg", "Kuyruk_yagi_fiyat_TL_kg",
    "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg", "Kilif_fiyat_TL_m",
    "Fason_birim_bedel_TL_kg_girdi", "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun",
]
CATEGORICAL = ["Bolge", "Recete_profili", "Isleme_modeli"]
FEATURES_A = NUMERIC + CATEGORICAL
FEATURES_B = FEATURES_A + LOSS


def score(y, pred, baseline, median_baseline=None):
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mean_baseline = float(baseline)
    median_baseline = mean_baseline if median_baseline is None else float(median_baseline)
    mae = float(mean_absolute_error(y, pred))
    mean_mae = float(mean_absolute_error(y, np.full(len(y), mean_baseline)))
    median_mae = float(mean_absolute_error(y, np.full(len(y), median_baseline)))
    return {
        "mae": mae,
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "r2": float(r2_score(y, pred)),
        "mean_baseline_mae": mean_mae,
        "median_baseline_mae_test_median_descriptive": median_mae,
        "improvement_over_mean_baseline_pct": 100 * (1 - mae / mean_mae) if mean_mae else 0.0,
        "test_records": int(len(y)),
    }


def pipeline(features, estimator):
    numeric = [x for x in features if x not in CATEGORICAL]
    prep = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])
    return Pipeline([("preprocess", prep), ("model", estimator)])


def main():
    df = pd.read_csv(DATA).replace([np.inf, -np.inf], np.nan)
    required = set(FEATURES_B + [TARGET_YIELD, TARGET_EKP, TARGET_COST])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Eksik kolonlar: {missing}")
    # Explicit, allow-listed predictors prevent target-derived and post-run columns entering X.
    for col in NUMERIC + LOSS + [TARGET_YIELD, TARGET_EKP, TARGET_COST]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET_YIELD, TARGET_EKP, TARGET_COST]).reset_index(drop=True)
    invalid_yield = int((df[TARGET_YIELD] <= 0).sum())
    invalid_cost = int((df[TARGET_COST] < 0).sum())
    if invalid_yield or invalid_cost:
        raise ValueError(
            f"Veri kalite hatası: net çıktı <= 0 olan {invalid_yield} kayıt, "
            f"negatif maliyetli {invalid_cost} kayıt var. Önce kaynak veriyi düzelt."
        )
    if len(df) != 1000:
        raise ValueError(f"Beklenen 1000 sentetik satır yerine {len(df)} kullanılabilir satır var.")
    train_i, test_i = train_test_split(np.arange(len(df)), test_size=0.2, random_state=42)
    train, test = df.iloc[train_i], df.iloc[test_i]
    result = {
        "dataset": "data/raw/sucuk_uretim_1000_simule_parti.csv",
        "synthetic_records": len(df), "train_records": len(train), "test_records": len(test),
        "data_quality_checks": {
            "invalid_nonpositive_yield_records": invalid_yield,
            "negative_total_cost_records": invalid_cost,
            "target_formula": "EKP_TL_kg = Toplam_parti_maliyeti_TL / Net_sucuk_ciktisi_kg_simule",
        },
        "split": {"method": "train_test_split", "test_size": 0.2, "random_state": 42},
        "data_limit": "1.000 kaydın tamamı sentetik/simüledir; workbook sözlüğü kayıp oranlarını gerçek tartım değil simülasyon olarak tanımlar. Sonuçlar gerçek fabrika performansını kanıtlamaz.",
        "leakage_audit": {
            "scenario_A_features": FEATURES_A,
            "scenario_B_only_additional_features": LOSS,
            "excluded_predictors": ["Toplam_parti_maliyeti_TL", TARGET_YIELD, TARGET_EKP,
                                    "Karisim_girdi_toplam_kg (türetilmiş girdi toplamı)",
                                    "gerçekleşmiş işçilik saati", "gerçekleşmiş elektrik tüketimi",
                                    "gerçekleşmiş maliyet bileşenleri", "Et_maliyet_payi_pct"],
            "measurement_timing": "XLSX Degisken_Sozlugu kayıp oranlarını simüle/gerçek tartım değil diye tanımlar. Girdi miktarı/kategori ve fiyat/tarife alanlarının parti bazlı zaman damgası yok; üretim öncesi erişilebilirliği gerçek veride doğrulanmalıdır.",
            "target_derived_fields_excluded": ["Karisim_girdi_toplam_kg", "Direkt_malzeme_toplam_TL", "Toplam_parti_maliyeti_TL", "EKP_TL_kg", "Et_maliyet_payi_pct"],
        },
        "ekp_integrity": {
            "formula": "Toplam_parti_maliyeti_TL / Net_sucuk_ciktisi_kg_simule",
            "units": "TL / kg net = TL/kg",
            "max_abs_ratio_difference_tl_per_kg": float(np.max(np.abs(df[TARGET_COST] / df[TARGET_YIELD] - df[TARGET_EKP]))),
            "mean_abs_ratio_difference_tl_per_kg": float(np.mean(np.abs(df[TARGET_COST] / df[TARGET_YIELD] - df[TARGET_EKP]))),
            "negative_cost_records": int((df[TARGET_COST] < 0).sum()),
            "nonpositive_yield_records": int((df[TARGET_YIELD] <= 0).sum()),
            "ekp_by_processing_mode": {
                str(mode): {"records": int(len(group)), "mean": float(group[TARGET_EKP].mean()),
                            "std": float(group[TARGET_EKP].std()), "min": float(group[TARGET_EKP].min()),
                            "median": float(group[TARGET_EKP].median()), "max": float(group[TARGET_EKP].max())}
                for mode, group in df.groupby("Isleme_modeli")
            },
        },
        "models": {},
    }
    candidates = {}
    predictions = {}
    # Yield A: production-before-known variables only.
    for name, estimator in [
        ("random_forest", RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
        ("extra_trees", ExtraTreesRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
    ]:
        model = pipeline(FEATURES_A, estimator).fit(train[FEATURES_A], train[TARGET_YIELD])
        pred = model.predict(test[FEATURES_A])
        candidates[("yield", name)] = model
        predictions[("yield", name)] = pred
        result["models"][f"yield_{name}_scenario_A"] = {
            "target": TARGET_YIELD, "features": FEATURES_A,
            "scenario": "A: production-before; feature timing remains to be confirmed",
            "metrics": score(test[TARGET_YIELD], pred, train[TARGET_YIELD].mean(), train[TARGET_YIELD].median()),
        }
    loss_known = test[LOSS].notna().all(axis=1).to_numpy()
    mass_pred = (test["Et_girdi_kg"] + test["Kuyruk_yagi_girdi_kg"] + test["Baharat_girdi_kg"] +
                 test["Tuz_girdi_kg"] + test["Diger_kucuk_girdi_kg"]) * (1 - test[LOSS[0]] / 100) * (1 - test[LOSS[1]] / 100)
    # This is an oracle diagnostic with realized losses; it is not a valid A forecast.
    result["models"]["yield_mass_balance_realized_loss_diagnostic"] = {
        "target": TARGET_YIELD, "features": ["ingredient inputs", *LOSS],
        "scenario": "Diagnostic only: realized loss values; unavailable pre-run unless verified planning assumptions",
        "metrics": score(test[TARGET_YIELD], mass_pred, train[TARGET_YIELD].mean(), train[TARGET_YIELD].median()),
        "formula": "ingredient input sum * (1-drying loss/100) * (1-trimming loss/100)",
    }
    if loss_known.any():
        b_test = test.loc[loss_known]
        model_b = pipeline(FEATURES_B, RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)).fit(train[FEATURES_B], train[TARGET_YIELD])
        pred_b = model_b.predict(b_test[FEATURES_B])
        candidates[("yield", "scenario_B")]=model_b
        result["models"]["yield_random_forest_scenario_B"] = {
            "target": TARGET_YIELD, "features": FEATURES_B,
            "scenario": "B: loss rates are user-entered planning assumptions; timing not established by dataset",
            "metrics": score(b_test[TARGET_YIELD], pred_b, train[TARGET_YIELD].mean()),
        }

    # EKP regressors use fixed training hyperparameters; no selection on holdout.
    for scenario, features in [("A", FEATURES_A), ("B", FEATURES_B)]:
        for name, estimator in [
            ("random_forest", RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
            ("extra_trees", ExtraTreesRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
        ]:
            model = pipeline(features, estimator).fit(train[features], train[TARGET_EKP])
            pred = model.predict(test[features])
            key = f"ekp_{name}_scenario_{scenario}"
            if scenario == "A":
                candidates[("ekp", f"{name}_{scenario}")] = model
            predictions[("ekp", f"{name}_{scenario}")] = pred
            result["models"][key] = {
                "target": TARGET_EKP, "features": features,
                "scenario": ("A: production-before features" if scenario == "A" else
                             "B: drying and trimming losses supplied as planning assumptions; timing unverified"),
                "metrics": score(test[TARGET_EKP], pred, train[TARGET_EKP].mean(), train[TARGET_EKP].median()),
            }
    # Cost-then-yield ratio: target cost is estimated from A-only predictors; actual cost/output never enter X.
    cost_model = pipeline(FEATURES_A, RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)).fit(train[FEATURES_A], train[TARGET_COST])
    yield_model = candidates[("yield", "random_forest")]
    cost_pred = cost_model.predict(test[FEATURES_A])
    yield_pred = yield_model.predict(test[FEATURES_A])
    result["models"]["total_cost_random_forest_scenario_A"] = {
        "target": TARGET_COST, "features": FEATURES_A,
        "scenario": "A total-cost predictor; realized total cost is target only, never a feature",
        "metrics": score(test[TARGET_COST], cost_pred, train[TARGET_COST].mean(), train[TARGET_COST].median()),
    }
    valid = np.isfinite(yield_pred) & (yield_pred > 0) & np.isfinite(cost_pred) & (cost_pred >= 0)
    ratio = cost_pred[valid] / yield_pred[valid]
    ratio_score = score(test[TARGET_EKP].to_numpy()[valid], ratio, train[TARGET_EKP].mean(), train[TARGET_EKP].median())
    result["models"]["ekp_predicted_cost_over_predicted_yield_scenario_A"] = {
        "target": TARGET_EKP, "features": FEATURES_A,
        "cost_target": TARGET_COST, "yield_model": "yield_random_forest_scenario_A",
        "scenario": "A; component-wise cost forecast is not supported by available pre-run measurements; estimates total cost then divides by predicted net output",
        "metrics": ratio_score, "invalid_nonpositive_yield_predictions": int((~valid).sum()),
    }
    # Save candidate models only; API production filenames remain untouched.
    MODELS.mkdir(exist_ok=True)
    for (kind, variant), model in candidates.items():
        joblib.dump({"model": model, "feature_columns": FEATURES_B if variant == "scenario_B" else (FEATURES_A + LOSS if variant.endswith("_B") else FEATURES_A),
                     "target": TARGET_YIELD if kind == "yield" else TARGET_EKP,
                     "scenario": variant}, MODELS / f"{kind}_{variant}_candidate.joblib")
    joblib.dump({"model": cost_model, "feature_columns": FEATURES_A, "target": TARGET_COST}, MODELS / "total_cost_scenario_A_candidate.joblib")
    result["candidate_model_files"] = sorted(p.name for p in MODELS.glob("*_candidate.joblib"))
    result["api_models_overwritten"] = False
    result["production_readiness"] = {
        "yield": "candidate only; synthetic-only evaluation; external validation required",
        "ekp": "NOT READY: synthetic-only data and weak Scenario A baseline improvement do not support production use",
        "scenario_B": "diagnostic only; loss-feature timing not verified; not saved as deployable candidate",
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "model_comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "training_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
