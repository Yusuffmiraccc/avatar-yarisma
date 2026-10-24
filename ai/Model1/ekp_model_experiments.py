# EKP model experiments — safe candidate evaluation, no production model overwrite.
# Copy this file into ai\\Model1, then run:
#   python .\\ekp_model_experiments.py
#
# Uses the existing synthetic CSV, tests multiple regressors under the same fixed split,
# compares each against a median baseline, and saves candidate models/reports only.
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold, cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.compose import TransformedTargetRegressor

ROOT = Path(__file__).resolve().parent
DATA_CANDIDATES = [
    ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv",
    ROOT / "data" / "raw" / "sucuk_uretim_gercek_veri_benchmarkli_1000_parti.xlsx",
]
OUT_MODELS = ROOT / "models" / "candidates"
OUT_REPORTS = ROOT / "reports"
OUT_MODELS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

TARGET_CANDIDATES = ["EKP_TL_kg", "EKP_TL_kg_simule", "Birim_uretim_maliyeti_TL_kg", "EKP"]
TARGET = None
df = None
source = None
for path in DATA_CANDIDATES:
    if not path.exists():
        continue
    try:
        if path.suffix.lower() == ".csv":
            candidate = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
        else:
            candidate = pd.read_excel(path, sheet_name="1000_Simule_Parti")
        found = next((c for c in TARGET_CANDIDATES if c in candidate.columns), None)
        if found:
            df, TARGET, source = candidate, found, path
            break
    except Exception:
        continue

if df is None:
    raise FileNotFoundError(
        "Hedef EKP sütunu otomatik bulunamadı. CSV/XLSX başlıklarını ve hedef sütun adını kontrol edin."
    )

# Only production-before-available features; intentionally excludes realized output, costs,
# simulated target, measured losses, and any fields that directly reveal the target.
feature_columns = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg", "Kilif_metre", "Et_fiyat_TL_kg",
    "Kuyruk_yagi_fiyat_TL_kg", "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg",
    "Kilif_fiyat_TL_m", "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun", "Bolge", "Recete_profili", "Isleme_modeli",
]
missing = [c for c in feature_columns if c not in df.columns]
if missing:
    raise ValueError(
        "CSV'de gerekli feature sütunları yok: " + ", ".join(missing) +
        "\nBulunan sütunlar: " + ", ".join(map(str, df.columns))
    )

work = df[feature_columns + [TARGET]].copy()
work[TARGET] = pd.to_numeric(work[TARGET], errors="coerce")
work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=[TARGET])
work = work[work[TARGET] > 0]
X, y = work[feature_columns], work[TARGET].astype(float)
if len(work) < 30:
    raise ValueError(f"Geçerli satır sayısı yetersiz: {len(work)}")

numeric = [c for c in feature_columns if c not in ["Bolge", "Recete_profili", "Isleme_modeli"]]
categorical = ["Bolge", "Recete_profili", "Isleme_modeli"]
preprocess = ColumnTransformer([
    ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
    ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                      ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
])
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

models = {
    "DummyMedian": DummyRegressor(strategy="median"),
    "RandomForest": RandomForestRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.9,
                                          random_state=42, n_jobs=-1),
    "ExtraTrees": ExtraTreesRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.9,
                                      random_state=42, n_jobs=-1),
    "RandomForest_LogTarget": TransformedTargetRegressor(
        regressor=RandomForestRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.9,
                                        random_state=42, n_jobs=-1),
        func=np.log1p, inverse_func=np.expm1
    ),
    "ExtraTrees_LogTarget": TransformedTargetRegressor(
        regressor=ExtraTreesRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.9,
                                      random_state=42, n_jobs=-1),
        func=np.log1p, inverse_func=np.expm1
    ),
}

results = []
fitted = {}
for name, estimator in models.items():
    pipe = Pipeline([("preprocess", preprocess), ("model", estimator)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(X_train, y_train)
    pred = np.asarray(pipe.predict(X_test), dtype=float)
    mae = mean_absolute_error(y_test, pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    r2 = r2_score(y_test, pred)
    results.append({"model": name, "n_train": len(X_train), "n_test": len(X_test),
                    "MAE_TL_kg": mae, "RMSE_TL_kg": rmse, "R2": r2})
    fitted[name] = pipe

result_df = pd.DataFrame(results).sort_values("MAE_TL_kg")
result_df.to_csv(OUT_REPORTS / "ekp_model_experiment_results.csv", index=False, encoding="utf-8-sig")
eligible = result_df[result_df["model"] != "DummyMedian"]
best_name = str(eligible.iloc[0]["model"])
best_pipe = fitted[best_name]
candidate_path = OUT_MODELS / "ekp_best_candidate.joblib"
joblib.dump({
    "model": best_pipe,
    "feature_columns": feature_columns,
    "target": TARGET,
    "scenario": "A_production_before",
    "data_source": str(source),
    "data_type": "synthetic",
    "production_ready": False,
    "test_split": {"test_size": 0.2, "random_state": 42},
}, candidate_path)

baseline = result_df[result_df.model == "DummyMedian"].iloc[0]
best = result_df[result_df.model == best_name].iloc[0]
improvement = (1 - float(best.MAE_TL_kg) / float(baseline.MAE_TL_kg)) * 100
lines = [
    "# EKP Model Deneyleri — Senaryo A",
    "",
    f"- Veri dosyası: `{source}`",
    f"- Veri türü: **sentetik**",
    f"- Geçerli kayıt: {len(work)}; eğitim: {len(X_train)}; test: {len(X_test)}",
    f"- Hedef: `{TARGET}`",
    "- Özellikler: üretim öncesi mevcut olduğu varsayılan 18 alan.",
    "- Dışarıda bırakılanlar: gerçekleşmiş maliyet/çıktı ve kuruma/ayıklama kaybı; olası hedef sızıntısını azaltmak için.",
    "- Bölme: `train_test_split(test_size=0.2, random_state=42)`; tüm adaylarda aynı test kümesi.",
    "",
    "## Test sonuçları",
    "",
    "| Model | MAE (TL/kg) | RMSE (TL/kg) | R² |",
    "|---|---:|---:|---:|",
]
for _, row in result_df.iterrows():
    lines.append(f"| {row.model} | {row.MAE_TL_kg:.4f} | {row.RMSE_TL_kg:.4f} | {row.R2:.4f} |")
lines += [
    "",
    f"## En iyi aday: {best_name}",
    f"- Medyan referans MAE: {float(baseline.MAE_TL_kg):.4f} TL/kg",
    f"- En iyi aday MAE: {float(best.MAE_TL_kg):.4f} TL/kg",
    f"- Referansa göre MAE değişimi: %{improvement:.2f} (pozitif = iyileşme).",
    f"- Aday dosyası: `{candidate_path}`",
    "",
    "## Yorum",
    "",
    "Bu deney yalnızca sentetik veri üzerindedir. Daha düşük test MAE'si, gerçek üretimde başarı kanıtı değildir. "
    "Aday model üretim modelinin üzerine yazılmamıştır. Üretime geçmeden önce anonimleştirilmiş gerçek parti kayıtlarında "
    "zamansal/bağımsız test, kalibrasyon ve veri kalitesi kontrolü gerekir.",
    "",
    "Harici yayımlanmış maliyet payları bu deneyin eğitim satırlarına eklenmemiştir; toplulaştırılmış oranlar parti bazlı EKP hedefi değildir.",
]
(OUT_REPORTS / "ekp_model_experiment_report.md").write_text("\n".join(lines), encoding="utf-8")
print(result_df.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
print(f"\nEn iyi aday: {best_name}; MAE iyileşmesi medyan referansa göre: %{improvement:.2f}")
print("Rapor:", OUT_REPORTS / "ekp_model_experiment_report.md")
print("Sonuç tablosu:", OUT_REPORTS / "ekp_model_experiment_results.csv")
print("Aday model:", candidate_path)
print("Üretim modelleri değiştirilmedi.")
