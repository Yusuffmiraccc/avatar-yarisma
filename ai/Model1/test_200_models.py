from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

DATA_CSV = ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv"
YIELD_MODEL_PATH = ROOT / "models" / "yield_model.joblib"
EKP_MODEL_PATH = ROOT / "models" / "ekp_model.joblib"

YIELD_TARGET = "Net_sucuk_ciktisi_kg_simule"
EKP_TARGET = "EKP_TL_kg"

# Model dosyalarının SHA-256 özetini al.
def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_model(path):
    obj = joblib.load(path)
    # Bazı modeller doğrudan pipeline, bazıları sözlük olarak saklanır.
    if isinstance(obj, dict):
        model = obj.get("model", obj.get("pipeline"))
        features = obj.get("feature_columns", obj.get("features"))
        if model is None:
            raise ValueError(f"{path.name}: model/pipeline anahtarı bulunamadı.")
        return model, list(features) if features is not None else None
    return obj, None

def get_features(model, saved_features, df, target):
    if saved_features:
        features = saved_features
    elif hasattr(model, "feature_names_in_"):
        features = list(model.feature_names_in_)
    else:
        # Yalnızca modelde özellik listesi kayıtlı değilse kullanılır.
        features = [
            "Et_girdi_kg",
            "Kuyruk_yagi_girdi_kg",
            "Baharat_girdi_kg",
            "Tuz_girdi_kg",
            "Diger_kucuk_girdi_kg",
            "Kilif_metre",
            "Et_birim_fiyat_TL_kg",
            "Kuyruk_yagi_birim_fiyat_TL_kg",
            "Baharat_birim_fiyat_TL_kg",
            "Tuz_birim_fiyat_TL_kg",
            "Diger_kucuk_birim_fiyat_TL_kg",
            "Kilif_birim_fiyat_TL_metre",
            "Isçilik_TL",
            "Enerji_TL",
            "Ambalaj_TL",
            "Bolge",
            "Recete_profili",
            "Isleme_modeli",
        ]
        features = [c for c in features if c in df.columns]

    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(
            f"{target}: veri setinde gerekli özellikler yok: {missing}"
        )
    return features

def metrics(y_true, y_pred, baseline_value):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    baseline = np.full(len(y_true), baseline_value, dtype=float)
    return {
        "n": int(len(y_true)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "baseline_median_MAE": float(mean_absolute_error(y_true, baseline)),
        "baseline_median_RMSE": float(np.sqrt(mean_squared_error(y_true, baseline))),
        "MAE_baseline_improvement_pct": float(
            (1 - mean_absolute_error(y_true, y_pred) /
             max(mean_absolute_error(y_true, baseline), 1e-12)) * 100
        ),
    }

def main():
    for path in (DATA_CSV, YIELD_MODEL_PATH, EKP_MODEL_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    hashes_before = {
        "yield_model.joblib": sha256(YIELD_MODEL_PATH),
        "ekp_model.joblib": sha256(EKP_MODEL_PATH),
    }

    df = pd.read_csv(DATA_CSV)
    required_targets = [YIELD_TARGET, EKP_TARGET]
    missing_targets = [c for c in required_targets if c not in df.columns]
    if missing_targets:
        raise ValueError(
            f"Veri setinde hedef sütunları bulunamadı: {missing_targets}"
        )

    # Eğitim koduyla aynı 80/20 indeks bölünmesi.
    train_idx, test_idx = train_test_split(
        np.arange(len(df)), test_size=0.2, random_state=42
    )
    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()

    if len(test_df) != 200:
        print(f"UYARI: Test kümesi 200 değil, {len(test_df)} kayıt.")

    yield_model, yield_saved_features = load_model(YIELD_MODEL_PATH)
    ekp_model, ekp_saved_features = load_model(EKP_MODEL_PATH)

    yield_features = get_features(
        yield_model, yield_saved_features, df, YIELD_TARGET
    )
    ekp_features = get_features(
        ekp_model, ekp_saved_features, df, EKP_TARGET
    )

    # Her model için referans değeri yalnızca eğitim bölümünden hesaplanır.
    yield_baseline = float(train_df[YIELD_TARGET].median())
    ekp_baseline = float(train_df[EKP_TARGET].median())

    actual_yield = test_df[YIELD_TARGET].astype(float).to_numpy()
    actual_ekp = test_df[EKP_TARGET].astype(float).to_numpy()

    pred_yield = np.asarray(
        yield_model.predict(test_df[yield_features]), dtype=float
    ).reshape(-1)
    pred_ekp = np.asarray(
        ekp_model.predict(test_df[ekp_features]), dtype=float
    ).reshape(-1)

    if len(pred_yield) != len(test_df) or len(pred_ekp) != len(test_df):
        raise ValueError("Tahmin sayısı test kayıtlarının sayısıyla uyuşmuyor.")

    results = test_df.copy()
    results.insert(0, "source_row_index", test_idx)
    results.insert(0, "test_no", np.arange(1, len(test_df) + 1))
    results["predicted_yield_kg"] = pred_yield
    results["yield_abs_error_kg"] = np.abs(actual_yield - pred_yield)
    results["yield_abs_pct_error"] = (
        np.abs(actual_yield - pred_yield) /
        np.maximum(np.abs(actual_yield), 1e-12) * 100
    )
    results["predicted_ekp_tl_kg"] = pred_ekp
    results["ekp_abs_error_tl_kg"] = np.abs(actual_ekp - pred_ekp)
    results["ekp_abs_pct_error"] = (
        np.abs(actual_ekp - pred_ekp) /
        np.maximum(np.abs(actual_ekp), 1e-12) * 100
    )

    csv_path = REPORTS / "test_200_model_results.csv"
    results.to_csv(csv_path, index=False, encoding="utf-8-sig")

    ekp_top = results.sort_values(
        "ekp_abs_error_tl_kg", ascending=False
    ).head(10)
    top_path = REPORTS / "test_200_ekp_top_errors.csv"
    ekp_top.to_csv(top_path, index=False, encoding="utf-8-sig")

    summary = {
        "dataset": str(DATA_CSV.relative_to(ROOT)),
        "dataset_rows": int(len(df)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "split": {"test_size": 0.2, "random_state": 42},
        "note": (
            "Bu test bölümü, modeller gerçekten aynı split ile eğitildiyse "
            "bağımsız test olarak yorumlanabilir. Veri simüle edilmiştir."
        ),
        "yield_model": metrics(actual_yield, pred_yield, yield_baseline),
        "ekp_model": metrics(actual_ekp, pred_ekp, ekp_baseline),
        "yield_features": yield_features,
        "ekp_features": ekp_features,
        "worst_ekp_cases": ekp_top[
            [
                "test_no", "source_row_index", EKP_TARGET,
                "predicted_ekp_tl_kg", "ekp_abs_error_tl_kg",
                "ekp_abs_pct_error"
            ]
        ].to_dict(orient="records"),
    }

    hashes_after = {
        "yield_model.joblib": sha256(YIELD_MODEL_PATH),
        "ekp_model.joblib": sha256(EKP_MODEL_PATH),
    }
    summary["model_hashes_before"] = hashes_before
    summary["model_hashes_after"] = hashes_after
    summary["model_files_unchanged"] = hashes_before == hashes_after

    json_path = REPORTS / "test_200_model_results.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n=== 200 KAYITLIK TEST SONUÇLARI ===")
    for label, key in (("NET ÇIKTI", "yield_model"), ("EKP", "ekp_model")):
        print(f"\n{label}")
        for metric, value in summary[key].items():
            print(f"  {metric}: {value:.4f}" if isinstance(value, float)
                  else f"  {metric}: {value}")

    print("\n=== EN BÜYÜK 10 EKP HATASI ===")
    print(ekp_top[
        ["test_no", EKP_TARGET, "predicted_ekp_tl_kg",
         "ekp_abs_error_tl_kg", "ekp_abs_pct_error"]
    ].to_string(index=False))

    print("\n=== DOSYALAR ===")
    print(csv_path)
    print(json_path)
    print(top_path)
    print(f"Model dosyaları değişmedi: {summary['model_files_unchanged']}")

if __name__ == "__main__":
    main()
