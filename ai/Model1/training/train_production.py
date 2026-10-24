from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor, ExtraTreesRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# Yalnızca üretim başlamadan bilinebilecek girdiler kullanılır.
NUMERIC_FEATURES = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg", "Kilif_metre", "Et_fiyat_TL_kg",
    "Kuyruk_yagi_fiyat_TL_kg", "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg",
    "Kilif_fiyat_TL_m", "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun"
]
CAT_FEATURES = ["Bolge", "Recete_profili", "Isleme_modeli"]
FEATURES = NUMERIC_FEATURES + CAT_FEATURES
TARGETS = {
    "yield_model_candidate.joblib": "Net_sucuk_ciktisi_kg_simule",
    "ekp_model_candidate.joblib": "EKP_TL_kg",
}

def main():
    df = pd.read_csv(DATA_PATH)
    missing = sorted(set(FEATURES + list(TARGETS.values())) - set(df.columns))
    if missing:
        raise ValueError(f"Veri setinde gerekli sütunlar eksik: {missing}")
    df = df[FEATURES + list(TARGETS.values())].replace([np.inf, -np.inf], np.nan)
    for col in NUMERIC_FEATURES + list(TARGETS.values()):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=list(TARGETS.values()))
    if len(df) < 30:
        raise ValueError(f"Eğitim için yeterli kayıt yok: {len(df)}")

    X = df[FEATURES]
    X_train, X_test, idx_train, idx_test = train_test_split(
        X, df.index, test_size=0.2, random_state=42
    )
    report = {
        "dataset": str(DATA_PATH.relative_to(ROOT)),
        "records_used": int(len(df)),
        "train_records": int(len(idx_train)),
        "test_records": int(len(idx_test)),
        "data_quality_warning": "Kayıtlar sentetik/simüle; metrikler gerçek işletme performansını temsil etmez.",
        "models": {}
    }

    for filename, target in TARGETS.items():
        y = df.loc[X_train.index, target]
        y_test = df.loc[X_test.index, target]
        numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
        categorical_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ])
        pre = ColumnTransformer([
            ("num", numeric_pipe, NUMERIC_FEATURES),
            ("cat", categorical_pipe, CAT_FEATURES)
        ])
        model = RandomForestRegressor(
            n_estimators=350, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=-1
        )
        pipe = Pipeline([("preprocess", pre), ("model", model)])
        pipe.fit(X_train, y)
        pred = pipe.predict(X_test)

        # Basit referans: eğitim kümesinin hedef ortalaması
        baseline_pred = np.full(len(y_test), float(y.mean()))
        metrics = {
            "mae": float(mean_absolute_error(y_test, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
            "r2": float(r2_score(y_test, pred)),
            "baseline_mean_mae": float(mean_absolute_error(y_test, baseline_pred)),
            "improvement_over_mean_baseline_pct": float(
                100 * (1 - mean_absolute_error(y_test, pred) / max(mean_absolute_error(y_test, baseline_pred), 1e-9))
            )
        }
        joblib.dump(pipe, MODEL_DIR / filename)
        report["models"][filename] = {"target": target, "metrics": metrics}
        print(f"\n{filename} -> {target}")
        for key, value in metrics.items():
            print(f"  {key}: {value:.4f}")

    report["api_models_overwritten"] = False
    report["data_limit"] = "1.000 kaydın tamamı sentetik/simüledir; sonuçlar gerçek fabrika performansını kanıtlamaz."
    report_path = REPORT_DIR / "production_training_candidate_metrics.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapor yazıldı: {report_path}")
    print("Aday modeller API'de kullanılan modellerin üzerine yazılmadı.")
    print("Not: Bunlar sentetik veri üzerindeki test metrikleridir; gerçek veriyle ayrıca doğrulanmalıdır.")

if __name__ == "__main__":
    main()
