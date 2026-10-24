"""Repeatable, leakage-aware EKP comparison; uses synthetic data and never writes model artifacts."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw/sucuk_uretim_1000_simule_parti.csv"
REPORTS = ROOT / "reports"
PRODUCTION = ROOT / "models/ekp_model.joblib"
OLD_CANDIDATE = ROOT / "models/candidates/ekp_best_candidate.joblib"
CANDIDATE_PATH = ROOT / "models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib"
TARGET = "EKP_TL_kg"
COST = "Toplam_parti_maliyeti_TL"
YIELD_TARGET = "Net_sucuk_ciktisi_kg_simule"
CATS = ["Bolge", "Recete_profili", "Isleme_modeli"]
NUMS = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg", "Kilif_metre", "Et_fiyat_TL_kg",
    "Kuyruk_yagi_fiyat_TL_kg", "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg",
    "Kilif_fiyat_TL_m", "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun",
]
FEATURES = NUMS + CATS
EXTRA = ["Planlanan_girdi_toplam_kg", "Dogrulanmis_malzeme_fason_TL", "Maliyet_alt_toplami_TL_kg_girdi"]


class PlannedCostFeatures(BaseEstimator, TransformerMixin):
    """Derive features only from the allowed plan quantities, prices, and process mode."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        frame = pd.DataFrame(X).copy()
        missing = sorted(set(FEATURES) - set(frame.columns))
        if missing:
            raise ValueError(f"Missing allow-listed EKP features: {missing}")
        qty = frame[["Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg",
                     "Tuz_girdi_kg", "Diger_kucuk_girdi_kg"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        material = (
            frame["Et_girdi_kg"] * frame["Et_fiyat_TL_kg"]
            + frame["Kuyruk_yagi_girdi_kg"] * frame["Kuyruk_yagi_fiyat_TL_kg"]
            + frame["Baharat_girdi_kg"] * frame["Baharat_fiyat_TL_kg"]
            + frame["Kilif_metre"] * frame["Kilif_fiyat_TL_m"]
        )
        fason = frame["Isleme_modeli"].astype(str).str.casefold().str.contains("fason")
        service = np.where(fason, qty * pd.to_numeric(frame["Fason_birim_bedel_TL_kg_girdi"], errors="coerce"), 0.0)
        subtotal = material + service
        frame["Planlanan_girdi_toplam_kg"] = qty
        frame["Dogrulanmis_malzeme_fason_TL"] = subtotal
        frame["Maliyet_alt_toplami_TL_kg_girdi"] = subtotal / qty.replace(0, np.nan)
        return frame


def known_subtotal(X):
    return PlannedCostFeatures().fit_transform(X)["Dogrulanmis_malzeme_fason_TL"].astype(float)


def preprocessor(engineered=False, scale_numeric=False):
    numeric = NUMS + (EXTRA if engineered else [])
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("num", Pipeline(numeric_steps), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATS),
    ], sparse_threshold=0.0)


def pipe(estimator, engineered=False, scale_numeric=False):
    steps = []
    if engineered:
        steps.append(("planned_cost_features", PlannedCostFeatures()))
    steps.extend([("preprocess", preprocessor(engineered, scale_numeric)), ("model", estimator)])
    return Pipeline(steps)


def score(y, pred):
    y, pred = np.asarray(y, dtype=float), np.asarray(pred, dtype=float)
    if not np.isfinite(pred).all():
        raise ValueError("A candidate produced non-finite predictions")
    return {
        "mae_tl_kg": float(mean_absolute_error(y, pred)),
        "rmse_tl_kg": float(np.sqrt(mean_squared_error(y, pred))),
        "r2": float(r2_score(y, pred)),
    }


def load_frame():
    data = pd.read_csv(DATA).replace([np.inf, -np.inf], np.nan)
    required = set(FEATURES + [TARGET, COST, YIELD_TARGET, "Veri_sinifi", "Fason_hizmet_TL"])
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing data columns: {missing}")
    def normalized(value):
        return "".join(
            char for char in unicodedata.normalize("NFKD", str(value)).casefold()
            if not unicodedata.combining(char)
        )
    synthetic = data["Veri_sinifi"].map(normalized).str.contains("sentetik|sim", regex=True)
    if data["Veri_sinifi"].isna().any() or not synthetic.all():
        raise ValueError("All rows must be explicitly marked synthetic/simulated")
    for col in NUMS + [TARGET, COST, YIELD_TARGET, "Fason_hizmet_TL"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if data[FEATURES + [TARGET, COST, YIELD_TARGET]].isna().any().any():
        raise ValueError("Missing/non-numeric model input or target")
    if (data[TARGET] <= 0).any() or (data[COST] < 0).any() or (data[YIELD_TARGET] <= 0).any():
        raise ValueError("Nonphysical target value")
    formula_err = data[COST] / data[YIELD_TARGET] - data[TARGET]
    input_kg = data[["Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg",
                     "Tuz_girdi_kg", "Diger_kucuk_girdi_kg"]].sum(axis=1)
    fason_mask = data["Isleme_modeli"].astype(str).str.casefold().str.contains("fason")
    fason_err = data.loc[fason_mask, "Fason_hizmet_TL"] - (
        input_kg.loc[fason_mask] * data.loc[fason_mask, "Fason_birim_bedel_TL_kg_girdi"]
    )
    checks = {
        "rows": int(len(data)),
        "all_rows_synthetic": True,
        "missing_required_cells": int(data[FEATURES + [TARGET, COST, YIELD_TARGET]].isna().sum().sum()),
        "duplicate_full_rows": int(data.duplicated().sum()),
        "duplicate_exact_feature_rows_including_repeats": int(data.duplicated(subset=FEATURES, keep=False).sum()),
        "ekp_formula_max_abs_diff_tl_kg": float(formula_err.abs().max()),
        "fason_formula_rows": int(fason_mask.sum()),
        "fason_rate_max_abs_diff_tl": float(fason_err.abs().max()),
    }
    return data.reset_index(drop=True), checks


def main():
    data, checks = load_frame()
    X, y = data[FEATURES].copy(), data[TARGET].astype(float)
    total_cost, net_yield = data[COST].astype(float), data[YIELD_TARGET].astype(float)

    candidates = {
        "dummy_mean": pipe(DummyRegressor(strategy="mean")),
        "dummy_median": pipe(DummyRegressor(strategy="median")),
        "random_forest_incumbent": pipe(RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
        "random_forest_log_target": pipe(TransformedTargetRegressor(
            regressor=RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1),
            func=np.log1p, inverse_func=np.expm1,
        )),
        "extra_trees": pipe(ExtraTreesRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1)),
        "hist_gradient_boosting": pipe(HistGradientBoostingRegressor(max_iter=150, max_leaf_nodes=15, learning_rate=0.05, l2_regularization=1.0, random_state=42)),
        "gradient_boosting_huber": pipe(GradientBoostingRegressor(loss="huber", n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=5, random_state=42)),
        "ridge": pipe(Ridge(alpha=10.0), scale_numeric=True),
        "huber_regressor": pipe(HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=1000), scale_numeric=True),
        "engineered_gradient_boosting_huber": pipe(
            GradientBoostingRegressor(loss="huber", n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=5, random_state=42),
            engineered=True,
        ),
    }
    cv = list(KFold(n_splits=5, shuffle=True, random_state=42).split(X, y))
    scores = {name: [] for name in candidates}
    scores["predicted_cost_over_predicted_yield_rf"] = []
    scores["hybrid_known_cost_plus_residual_over_predicted_yield"] = []
    rf_cost = pipe(RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1))
    rf_yield = pipe(RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1))
    residual_model = pipe(RandomForestRegressor(n_estimators=350, min_samples_leaf=2, max_features=0.9, random_state=42, n_jobs=-1), engineered=True)

    for train_i, valid_i in cv:
        xtr, xval = X.iloc[train_i], X.iloc[valid_i]
        for name, spec in candidates.items():
            model = clone(spec).fit(xtr, y.iloc[train_i])
            scores[name].append(score(y.iloc[valid_i], model.predict(xval)))
        cost_model = clone(rf_cost).fit(xtr, total_cost.iloc[train_i])
        yield_model = clone(rf_yield).fit(xtr, net_yield.iloc[train_i])
        scores["predicted_cost_over_predicted_yield_rf"].append(
            score(y.iloc[valid_i], cost_model.predict(xval) / yield_model.predict(xval))
        )
        known_tr, known_val = known_subtotal(xtr), known_subtotal(xval)
        resid = total_cost.iloc[train_i].to_numpy() - known_tr.to_numpy()
        hybrid_cost = clone(residual_model).fit(xtr, resid)
        hybrid_yield = clone(rf_yield).fit(xtr, net_yield.iloc[train_i])
        scores["hybrid_known_cost_plus_residual_over_predicted_yield"].append(
            score(y.iloc[valid_i], (known_val.to_numpy() + hybrid_cost.predict(xval)) / hybrid_yield.predict(xval))
        )

    train_i, test_i = train_test_split(np.arange(len(data)), test_size=0.2, random_state=42)
    xtr, xte = X.iloc[train_i], X.iloc[test_i]
    ytr, yte = y.iloc[train_i], y.iloc[test_i]
    holdout = {}
    for name, spec in candidates.items():
        fitted = clone(spec).fit(xtr, ytr)
        holdout[name] = score(yte, fitted.predict(xte))

    cost_fit = clone(rf_cost).fit(xtr, total_cost.iloc[train_i])
    yield_fit = clone(rf_yield).fit(xtr, net_yield.iloc[train_i])
    holdout["predicted_cost_over_predicted_yield_rf"] = score(yte, cost_fit.predict(xte) / yield_fit.predict(xte))
    known_tr, known_te = known_subtotal(xtr), known_subtotal(xte)
    residual_fit = clone(residual_model).fit(xtr, total_cost.iloc[train_i].to_numpy() - known_tr.to_numpy())
    hybrid_yield_fit = clone(rf_yield).fit(xtr, net_yield.iloc[train_i])
    holdout["hybrid_known_cost_plus_residual_over_predicted_yield"] = score(
        yte, (known_te.to_numpy() + residual_fit.predict(xte)) / hybrid_yield_fit.predict(xte)
    )

    cv_metrics = {}
    for name, folds in scores.items():
        cv_metrics[name] = {
            metric: {"mean": float(np.mean([item[metric] for item in folds])),
                     "std": float(np.std([item[metric] for item in folds], ddof=1))}
            for metric in folds[0]
        }
    median_mae = cv_metrics["dummy_median"]["mae_tl_kg"]["mean"]
    for values in cv_metrics.values():
        values["mae_improvement_over_median_baseline_pct"] = float(100 * (1 - values["mae_tl_kg"]["mean"] / median_mae))
    ranking = sorted(
        (name for name in cv_metrics if name not in {"dummy_mean", "dummy_median"}),
        key=lambda name: cv_metrics[name]["mae_tl_kg"]["mean"],
    )
    leader = ranking[0] if ranking else None
    incumbent_cv = cv_metrics["random_forest_incumbent"]
    leader_cv = cv_metrics.get(leader, {}) if leader else {}
    all_cv_metrics_improved = bool(leader and all(
        leader_cv[metric]["mean"] < incumbent_cv[metric]["mean"]
        if metric != "r2" else leader_cv[metric]["mean"] > incumbent_cv[metric]["mean"]
        for metric in ["mae_tl_kg", "rmse_tl_kg", "r2"]
    ))
    candidate_saved = False
    candidate_created_this_run = False
    candidate_metadata = {"saved": False, "production_ready": False}
    if leader == "engineered_gradient_boosting_huber" and all_cv_metrics_improved:
        candidate_package = None
        if CANDIDATE_PATH.exists():
            candidate_package = joblib.load(CANDIDATE_PATH)
            if candidate_package.get("feature_columns") != FEATURES or candidate_package.get("production_ready") is not False:
                raise ValueError("Existing separate research candidate has an unexpected feature contract/status")
        else:
            research_model = clone(candidates[leader]).fit(xtr, ytr)
            candidate_package = {
                "model": research_model,
                "feature_columns": FEATURES,
                "target": TARGET,
                "scenario": "A_preproduction_input_only_exploratory",
                "data_type": "synthetic",
                "production_ready": False,
                "training_records": int(len(train_i)),
                "holdout_metrics_exploratory": holdout[leader],
                "cv_metrics": cv_metrics[leader],
                "note": "Research candidate only. The fixed holdout was reused in prior experiments; external real-world validation is required.",
            }
            joblib.dump(candidate_package, CANDIDATE_PATH)
            candidate_created_this_run = True
        candidate_saved = True
        candidate_metadata = {
            "saved": True,
            "file": "models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib",
            "production_ready": False,
            "created_this_run": candidate_created_this_run,
            "training_records": candidate_package.get("training_records"),
            "holdout_metrics_exploratory": candidate_package.get("holdout_metrics_exploratory"),
        }
    median_holdout = score(yte, np.full(len(yte), float(ytr.median())))
    mean_holdout = score(yte, np.full(len(yte), float(ytr.mean())))
    for values in holdout.values():
        values["mae_improvement_over_training_median_baseline_pct"] = float(
            100 * (1 - values["mae_tl_kg"] / median_holdout["mae_tl_kg"])
        )

    production = {"available": False}
    if PRODUCTION.is_file():
        model = joblib.load(PRODUCTION)
        expected = list(getattr(model, "feature_names_in_", []))
        if expected and expected != FEATURES:
            raise ValueError("Production artifact feature names/order do not match Scenario A")
        production = {
            "available": True,
            "file": "models/ekp_model.joblib",
            "test_metrics": score(yte, model.predict(xte)),
            "sha256": hashlib.sha256(PRODUCTION.read_bytes()).hexdigest(),
            "feature_contract_matches": True,
        }
    old_candidate = {"available": False}
    if OLD_CANDIDATE.is_file():
        package = joblib.load(OLD_CANDIDATE)
        model = package["model"] if isinstance(package, dict) else package
        if isinstance(package, dict) and package.get("feature_columns") != FEATURES:
            raise ValueError("Prior candidate feature contract differs from Scenario A")
        old_candidate = {
            "available": True,
            "file": "models/candidates/ekp_best_candidate.joblib",
            "data_type": package.get("data_type", "unrecorded") if isinstance(package, dict) else "unrecorded",
            "production_ready": package.get("production_ready", False) if isinstance(package, dict) else False,
            "test_metrics": score(yte, model.predict(xte)),
            "note": "Previously selected using this same holdout; exploratory only.",
        }

    group_metrics = {}
    if production["available"]:
        preds = joblib.load(PRODUCTION).predict(xte)
        sub = data.iloc[test_i].copy()
        sub["_actual"], sub["_predicted"] = yte.to_numpy(), preds
        for col in CATS:
            group_metrics[col] = {}
            for label, group in sub.groupby(col):
                group_metrics[col][str(label)] = {
                    "n": int(len(group)),
                    "mae_tl_kg": float(np.mean(np.abs(group["_actual"] - group["_predicted"]))),
                    "small_group_descriptive_only": len(group) < 15,
                }

    ranking_table = []
    for name, vals in cv_metrics.items():
        h = holdout.get(name, {})
        ranking_table.append({
            "model": name,
            "cv_mae_mean_tl_kg": vals["mae_tl_kg"]["mean"],
            "cv_mae_std_tl_kg": vals["mae_tl_kg"]["std"],
            "cv_rmse_mean_tl_kg": vals["rmse_tl_kg"]["mean"],
            "cv_rmse_std_tl_kg": vals["rmse_tl_kg"]["std"],
            "cv_r2_mean": vals["r2"]["mean"],
            "cv_r2_std": vals["r2"]["std"],
            "cv_mae_improvement_over_median_baseline_pct": vals["mae_improvement_over_median_baseline_pct"],
            "fixed_holdout_mae_tl_kg": h.get("mae_tl_kg"),
            "fixed_holdout_rmse_tl_kg": h.get("rmse_tl_kg"),
            "fixed_holdout_r2": h.get("r2"),
        })

    report = {
        "dataset": "data/raw/sucuk_uretim_1000_simule_parti.csv",
        "data_type": "synthetic/simulated only",
        "real_factory_validation": False,
        "target": TARGET,
        "target_definition": "Toplam_parti_maliyeti_TL / Net_sucuk_ciktisi_kg_simule; TL/kg",
        "target_distribution": {
            "count": int(y.count()), "mean": float(y.mean()), "std": float(y.std()),
            "median": float(y.median()), "min": float(y.min()), "p01": float(y.quantile(.01)),
            "p99": float(y.quantile(.99)), "max": float(y.max()),
        },
        "data_integrity": checks,
        "scenario_A": {
            "features": FEATURES,
            "excluded": [TARGET, COST, YIELD_TARGET, "Kuruma_kaybi_pct", "Ayiklama_fire_pct",
                         "actual labor/kWh", "realized cost components", "Parti_ID", "Tarih_simulasyon"],
            "timing_limit": "The synthetic file does not prove timestamped pre-production availability of prices/tariffs. Confirm with real plan snapshots.",
        },
        "scenario_B": {
            "status": "not a pre-production candidate",
            "features": ["Kuruma_kaybi_pct", "Ayiklama_fire_pct"],
            "reason": "Synthetic loss values; their real measurement/availability time is unverified.",
        },
        "validation": {
            "primary": "5-fold shuffled cross-validation on all synthetic rows; all preprocessing fitted within each training fold.",
            "cv": {"n_splits": 5, "shuffle": True, "random_state": 42, "metrics": cv_metrics},
            "secondary_holdout": {
                "split": {"test_size": 0.2, "random_state": 42},
                "train_n": int(len(train_i)), "test_n": int(len(test_i)),
                "note": "This split has already been used in previous experiments; results are exploratory, not independent final validation.",
                "training_mean_baseline": mean_holdout,
                "training_median_baseline": median_holdout,
                "metrics": holdout,
            },
            "production_artifact": production,
            "previous_candidate": old_candidate,
            "new_research_candidate": candidate_metadata,
            "production_artifact_group_errors": group_metrics,
            "cv_mae_ranked_candidates": ranking,
            "cv_leader": ranking[0] if ranking else None,
        },
        "architectures": {
            "direct_EKP": "Compared baselines, RF, log-target RF, ExtraTrees, HistGradientBoosting, Huber GradientBoosting, Ridge and HuberRegressor.",
            "component_cost_over_yield": "Cost and net yield fit separately on each training fold, then predicted cost divided by predicted yield.",
            "hybrid": "Verified planned material and conditional fason subtotal + predicted remaining cost, divided by separately predicted yield. Salt/other, in-house cost, packaging and overhead lack a verified pre-production formula.",
        },
        "decision": {
            "production_model_changed": False,
            "candidate_artifact_saved": candidate_saved,
            "ekp_production_ready": False,
            "reason": "Synthetic-only data, weak Scenario A evidence, and no untouched real/time-based validation. The production artifact remains unchanged.",
        },
        "limitations": [
            "Synthetic model metrics are not factory performance.",
            "The fixed holdout has been used in previous experiments.",
            "CV estimates one simulated population; no verified production group/time identifier exists.",
            "Hashes establish file integrity only, not trusted origin or scientific validity.",
            "External cost-share benchmark is aggregated and not batch-level EKP training data.",
        ],
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "ekp_improvement_comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(ranking_table).sort_values("cv_mae_mean_tl_kg").to_csv(
        REPORTS / "ekp_improvement_comparison.csv", index=False, encoding="utf-8-sig"
    )

    lines = [
        "# EKP iyileştirme ve doğrulama karşılaştırması", "",
        "## Karar", "",
        "Verinin tamamı sentetik/simüledir; gerçek fabrika doğrulaması yoktur. Tahmin hatasını ölçtüm, hedef EKP değerlerini yapay olarak değiştirmedim. Üretim artefaktı korunmuş, yeni model üretime alınmamıştır.",
        "", "## Formül ve veri", "",
        "EKP = toplam parti maliyeti (TL) / net çıktı (kg), sonuç TL/kg'dır.",
        f"- 1.000 sentetik satır; EKP oran formülü maksimum farkı {checks['ekp_formula_max_abs_diff_tl_kg']:.6f} TL/kg.",
        f"- Fason hizmet formülü, {checks['fason_formula_rows']} Fason satırında maksimum {checks['fason_rate_max_abs_diff_tl']:.6f} TL farkla doğrulandı.",
        f"- Tam tekrarlar: {checks['duplicate_full_rows']}; tam aynı özellik imzalı satırlar: {checks['duplicate_exact_feature_rows_including_repeats']}.",
        "- Üretim öncesi senaryo A sadece girdi miktarları, kategori ve fiyat/tarife alanlarını kullanır. Fiyat/tarifelerin üretim öncesi zaman damgası sentetik kaynakta kanıtlanmadığından gerçek sistemde ayrıca doğrulanmalıdır.",
        "- Senaryo B kayıp yüzdelerini içerir. Bunlar sentetik olup gerçek ölçüm/erişilebilirlik zamanı belli değildir; B üretim adayı değildir.",
        "", "## 5 katlı çapraz doğrulama", "",
        "Aynı karıştırılmış fold'lar kullanıldı; ön işleme her fold'un eğitim kısmında öğrenildi. MAE/RMSE TL/kg. Baseline farkı, fold bazlı medyan DummyRegressor'a göre hesaplandı.",
        "", "| Model | CV MAE ort ± std | CV RMSE ort ± std | CV R² ort ± std | Medyan baseline'a göre MAE |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(ranking_table, key=lambda r: r["cv_mae_mean_tl_kg"]):
        lines.append(
            f"| {row['model']} | {row['cv_mae_mean_tl_kg']:.4f} ± {row['cv_mae_std_tl_kg']:.4f} | "
            f"{row['cv_rmse_mean_tl_kg']:.4f} ± {row['cv_rmse_std_tl_kg']:.4f} | "
            f"{row['cv_r2_mean']:.4f} ± {row['cv_r2_std']:.4f} | %{row['cv_mae_improvement_over_median_baseline_pct']:.2f} |"
        )
    lines += [
        "", f"CV MAE lideri {ranking[0] if ranking else 'yok'} olarak belirlendi; bu sentetik aday sıralamasıdır, üretim seçimi değildir.",
        "", "## Mimari ve daha önce kullanılan holdout", "",
        "Bileşen yaklaşımı maliyet ve net çıktıyı ayrı tahmin edip böler. Hibrit yaklaşım doğrulanmış formül alt toplamlarını kullanıp kalan maliyeti ve net çıktıyı ayrı tahmin eder. Gerçekleşmiş maliyet veya net çıktı hiçbir tahmin girdisi değildir.",
        "Sabit 800/200 holdout önceki deneylerde kullanıldığı için sonuçları keşifseldir ve bağımsız son test değildir.",
        "", "| Model | Holdout MAE | Holdout RMSE | Holdout R² | Eğitim medyanına göre MAE farkı |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, val in sorted(holdout.items(), key=lambda item: item[1]["mae_tl_kg"]):
        lines.append(
            f"| {name} | {val['mae_tl_kg']:.4f} | {val['rmse_tl_kg']:.4f} | {val['r2']:.4f} | %{val['mae_improvement_over_training_median_baseline_pct']:.2f} |"
        )
    if production["available"]:
        p = production["test_metrics"]
        lines.append(f"\nMevcut API üretim artefaktı: MAE {p['mae_tl_kg']:.4f}, RMSE {p['rmse_tl_kg']:.4f}, R² {p['r2']:.4f}; SHA-256 {production['sha256']}.")
    if old_candidate["available"]:
        p = old_candidate["test_metrics"]
        lines.append(f"Önceki log-target aday (aynı holdout ile seçildi): MAE {p['mae_tl_kg']:.4f}, RMSE {p['rmse_tl_kg']:.4f}, R² {p['r2']:.4f}; yalnızca keşifseldir.")
    lines += [
        "", "## Sonraki koşullar", "",
        "EKP modeli gerçek üretim için hazır değildir. Gerçek plan girdilerinin zaman damgaları, ayrı planlanan/gerçekleşmiş kayıp oranları, net tartım ve maliyet mutabakatı toplanmalı; en yeni gerçek partiler dokunulmamış zaman bazlı testte değerlendirilmelidir.",
        "", (f"Araştırma adayı ayrı dosyada: {candidate_metadata['file']}. Yalnızca eğitim bölmesinde fit edilmiştir; üretime hazır değildir." if candidate_saved else "Araştırma adayı oluşturulmadı."),
        "Makinece okunabilir ayrıntılar: reports/ekp_improvement_comparison.json ve reports/ekp_improvement_comparison.csv.",
    ]
    (REPORTS / "ekp_improvement_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "cv_mae_ranking": ranking,
        "cv_metrics": cv_metrics,
        "fixed_holdout_metrics": holdout,
        "production_artifact": production,
        "prior_candidate": old_candidate,
        "new_research_candidate": candidate_metadata,
        "reports": ["reports/ekp_improvement_report.md", "reports/ekp_improvement_comparison.json", "reports/ekp_improvement_comparison.csv"],
        "production_model_changed": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

