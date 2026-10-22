"""Saf ML mantığı (DB'siz): eğitim, çapraz doğrulama, baseline karşılaştırması, tahmin.

Dürüstlük kuralları: her zaman basit bir baseline ile karşılaştırılır; örnek sayısı azsa model yerine
baseline kullanılır ve sınırlılık notu üretilir; performans iddiası yalnızca ölçülen metriklerdir.
"""

from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MIN_SAMPLES = 30
PROD_NUM = ["total_input_kg", "main_share", "other_ratio", "cost_per_kg", "month"]
PROD_CAT = ["supplier_id"]
BUT_NUM = ["input_weight"]
BUT_CAT = ["animal_type"]


def _metrics(actual: np.ndarray, pred: np.ndarray) -> dict:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    err = pred - actual
    nz = actual != 0
    ss_tot = float(((actual - actual.mean()) ** 2).sum())
    return {
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "mape_percent": float((np.abs(err[nz]) / np.abs(actual[nz])).mean() * 100) if nz.any() else None,
        "r2": float(1 - (err ** 2).sum() / ss_tot) if ss_tot > 0 else None,
        "n": int(len(actual)),
    }


def _improvement(base: dict, model: dict) -> float | None:
    return round((1 - model["mae"] / base["mae"]) * 100, 2) if base["mae"] else None


def _pipe(estimator, num, cat, scale: bool) -> Pipeline:
    pre = ColumnTransformer([
        ("num", StandardScaler() if scale else "passthrough", num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ])
    return Pipeline([("pre", pre), ("est", estimator)])


# ----------------------------------------------------------------------------------------------- A
def train_production(df: pd.DataFrame) -> dict:
    """Hedef: yield_ratio (çıktı paket / girdi kg). EKP, tahmin edilen miktardan türetilir."""
    n = len(df)
    now = datetime.now(timezone.utc)
    version = f"prod-yield-{now:%Y%m%d%H%M%S}-n{n}"
    limitations = ["Eğitim verisi örnek/sentetik olabilir; gerçek üretici verisiyle yeniden eğitilmelidir.",
                   "Yalnızca geçmiş tamamlanmış üretim emirlerine dayanır; kalite/arıza gibi dış etkenler yoktur."]
    base_mean = float(df["yield_ratio"].mean()) if n else 0.0
    if n < MIN_SAMPLES:
        return {"kind": "production_yield", "version": version + "-baseline-only", "trained_at": now.isoformat(),
                "n_samples": n, "model": None, "baseline": {"mean_yield_ratio": base_mean}, "sigma_yield": 0.0,
                "metrics": None, "model_name": "BASELINE_MEAN",
                "limitations": limitations + [f"Örnek sayısı ({n}) {MIN_SAMPLES} altında: model eğitilmedi, baseline kullanılıyor."]}
    X, y = df[PROD_NUM + PROD_CAT], df["yield_ratio"].to_numpy()
    candidates = {
        "RIDGE": lambda: _pipe(Ridge(alpha=1.0), PROD_NUM, PROD_CAT, True),
        "GRADIENT_BOOSTING": lambda: _pipe(GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05,
                                                                       random_state=0), PROD_NUM, PROD_CAT, False),
    }
    kf = KFold(5, shuffle=True, random_state=42)
    oof = {k: np.zeros(n) for k in candidates}
    oof_base = np.zeros(n)
    for tr, te in kf.split(X):
        oof_base[te] = y[tr].mean()
        for k, mk in candidates.items():
            oof[k][te] = mk().fit(X.iloc[tr], y[tr]).predict(X.iloc[te])

    def to_qty(yield_pred):  # tahmin edilen verimden miktar ve EKP
        qty = yield_pred * df["total_input_kg"].to_numpy()
        ekp = df["input_cost"].to_numpy() / qty + df["service_unit_price"].to_numpy()
        return qty, ekp

    q_act, e_act = df["output_qty"].to_numpy(), df["ekp"].to_numpy()
    report = {}
    for name, pred in [("BASELINE_MEAN", oof_base), *oof.items()]:
        q, e = to_qty(pred)
        report[name] = {"output_quantity": _metrics(q_act, q), "ekp": _metrics(e_act, e), "yield_ratio": _metrics(y, pred)}
    best = min(candidates, key=lambda k: report[k]["output_quantity"]["mae"])
    # zaman bazlı holdout (son %20)
    order = np.argsort(df["completed_ts"].to_numpy())
    cut = int(n * 0.8)
    tr, te = order[:cut], order[cut:]
    holdout_model = candidates[best]().fit(X.iloc[tr], y[tr])
    hp, hb = holdout_model.predict(X.iloc[te]), np.full(len(te), y[tr].mean())
    sub = df.iloc[te]
    hq = lambda p: (p * sub["total_input_kg"].to_numpy(), sub["input_cost"].to_numpy() / (p * sub["total_input_kg"].to_numpy()) + sub["service_unit_price"].to_numpy())
    holdout = {"split": "son %20 (zaman sıralı)", "n_test": int(len(te)),
               "model": {"output_quantity": _metrics(sub["output_qty"], hq(hp)[0]), "ekp": _metrics(sub["ekp"], hq(hp)[1])},
               "baseline": {"output_quantity": _metrics(sub["output_qty"], hq(hb)[0]), "ekp": _metrics(sub["ekp"], hq(hb)[1])}}
    final = candidates[best]().fit(X, y)
    sigma = float(np.std(oof[best] - y, ddof=1))
    cv = {"folds": 5, "selected_model": best, "by_model": report,
          "improvement_over_baseline_percent": {
              "output_quantity_mae": _improvement(report["BASELINE_MEAN"]["output_quantity"], report[best]["output_quantity"]),
              "ekp_mae": _improvement(report["BASELINE_MEAN"]["ekp"], report[best]["ekp"])}}
    return {"kind": "production_yield", "version": version, "trained_at": now.isoformat(), "n_samples": n,
            "model": final, "baseline": {"mean_yield_ratio": base_mean}, "sigma_yield": sigma, "model_name": best,
            "metrics": {"cross_validation": cv, "temporal_holdout": holdout}, "limitations": limitations}


def predict_production(art: dict, f: dict) -> dict:
    """f: total_input_kg, main_share, other_ratio, cost_per_kg, month, supplier_id, input_cost, service_unit_price"""
    base_y = art["baseline"]["mean_yield_ratio"]
    used_model = art["model"] is not None
    if used_model:
        row = pd.DataFrame([{k: f[k] for k in PROD_NUM + PROD_CAT}])
        y = float(art["model"].predict(row)[0])
    else:
        y = base_y
    out = {}
    for tag, yy in (("model", y), ("baseline", base_y)):
        qty = yy * f["total_input_kg"]
        out[tag] = {"yield_ratio": yy, "output_quantity": qty,
                    "ekp": f["input_cost"] / qty + f["service_unit_price"]}
    half = 1.96 * art["sigma_yield"] * f["total_input_kg"]
    out["interval_95_output_quantity"] = [max(out["model"]["output_quantity"] - half, 0.0), out["model"]["output_quantity"] + half]
    out["used_model"] = used_model
    return out


# ----------------------------------------------------------------------------------------------- B
def train_butchering(df: pd.DataFrame, targets: list[str]) -> dict:
    """df: animal_type, input_weight, r_<kod> oranları. Hedef: her parça için ağırlık oranı."""
    n = len(df)
    now = datetime.now(timezone.utc)
    version = f"butchering-output-{now:%Y%m%d%H%M%S}-n{n}"
    cols = [f"r_{t}" for t in targets]
    limitations = ["Eğitim verisi örnek/sentetik olabilir; gerçek kesim kayıtlarıyla yeniden eğitilmelidir.",
                   "Oranlar hayvan türü ve girdi ağırlığına bağlı modellenir; ırk, yaş ve beslenme gibi etkenler yoktur."]
    base_by_animal = {a: g[cols].mean().to_dict() for a, g in df.groupby("animal_type")} if n else {}
    base_all = df[cols].mean().to_dict() if n else {}
    if n < MIN_SAMPLES:
        return {"kind": "butchering_output", "version": version + "-baseline-only", "trained_at": now.isoformat(),
                "n_samples": n, "model": None, "targets": targets, "baseline": {"by_animal": base_by_animal, "all": base_all},
                "sigma": {c: 0.0 for c in cols}, "metrics": None, "model_name": "BASELINE_ANIMAL_MEAN",
                "limitations": limitations + [f"Örnek sayısı ({n}) {MIN_SAMPLES} altında: model eğitilmedi, baseline kullanılıyor."]}
    X, Y = df[BUT_NUM + BUT_CAT], df[cols].to_numpy()
    w = df["input_weight"].to_numpy()
    cands = {
        "RIDGE": lambda: _pipe(Ridge(alpha=1.0), BUT_NUM, BUT_CAT, True),
        "RANDOM_FOREST": lambda: _pipe(RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1),
                                      BUT_NUM, BUT_CAT, False),
    }
    kf = KFold(5, shuffle=True, random_state=42)
    oof = {k: np.zeros_like(Y) for k in cands}
    oof_base = np.zeros_like(Y)
    for tr, te in kf.split(X):
        means = df.iloc[tr].groupby("animal_type")[cols].mean()
        glob = df.iloc[tr][cols].mean()
        for pos, i in enumerate(te):
            a = df["animal_type"].iloc[i]
            oof_base[i] = (means.loc[a] if a in means.index else glob).to_numpy()
        for k, mk in cands.items():
            oof[k][te] = mk().fit(X.iloc[tr], Y[tr]).predict(X.iloc[te])

    def kg_metrics(pred_ratio):
        act_kg, pred_kg = Y * w[:, None], pred_ratio * w[:, None]
        per = {t: _metrics(act_kg[:, j], pred_kg[:, j]) for j, t in enumerate(targets)}
        total = {"mae_kg": float(np.abs(pred_kg - act_kg).mean()),
                 "wmape_percent": float(np.abs(pred_kg - act_kg).sum() / act_kg.sum() * 100)}
        return {"per_product": per, "overall": total}

    report = {"BASELINE_ANIMAL_MEAN": kg_metrics(oof_base), **{k: kg_metrics(v) for k, v in oof.items()}}
    best = min(cands, key=lambda k: report[k]["overall"]["mae_kg"])
    final = cands[best]().fit(X, Y)
    sigma = {c: float(np.std(oof[best][:, j] - Y[:, j], ddof=1)) for j, c in enumerate(cols)}
    base = report["BASELINE_ANIMAL_MEAN"]["overall"]
    mod = report[best]["overall"]
    cv = {"folds": 5, "selected_model": best, "by_model": report,
          "improvement_over_baseline_percent": {"overall_mae_kg": round((1 - mod["mae_kg"] / base["mae_kg"]) * 100, 2)}}
    return {"kind": "butchering_output", "version": version, "trained_at": now.isoformat(), "n_samples": n, "model": final,
            "targets": targets, "baseline": {"by_animal": base_by_animal, "all": base_all}, "sigma": sigma,
            "model_name": best, "metrics": {"cross_validation": cv}, "limitations": limitations}


def predict_butchering(art: dict, animal_type: str, input_weight: float) -> dict:
    targets, cols = art["targets"], [f"r_{t}" for t in art["targets"]]
    base = art["baseline"]["by_animal"].get(animal_type)
    known = base is not None
    base = base or art["baseline"]["all"]
    if art["model"] is not None and known:
        ratios = art["model"].predict(pd.DataFrame([{"input_weight": input_weight, "animal_type": animal_type}]))[0]
        used_model = True
    else:
        ratios, used_model = np.array([base[c] for c in cols]), False
    parts = {}
    for j, t in enumerate(targets):
        half = 1.96 * art["sigma"][cols[j]] * input_weight
        pred = float(max(ratios[j], 0.0)) * input_weight
        parts[t] = {"predicted_weight": pred, "baseline_weight": float(base[cols[j]]) * input_weight,
                    "interval_95": [max(pred - half, 0.0), pred + half]}
    return {"parts": parts, "used_model": used_model, "animal_type_known": known}


def save(art: dict, path: str) -> None:
    joblib.dump(art, path)


def load(path: str) -> dict:
    return joblib.load(path)
