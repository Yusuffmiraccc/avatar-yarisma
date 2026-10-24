import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.model_selection import KFold, cross_validate
from sklearn.dummy import DummyRegressor

DATA = "data/raw/sucuk_uretim_1000_simule_parti.csv"
OUT = "reports/ekp_feature_experiments.csv"

df = pd.read_csv(DATA)
target = "EKP_TL_kg"

# Yalnızca tahmin anında kullanılabilecek aday girdiler.
numeric_base = [
    "Et_girdi_kg",
    "Kuyruk_yagi_girdi_kg",
    "Baharat_girdi_kg",
    "Tuz_girdi_kg",
    "Diger_kucuk_girdi_kg",
    "Karisim_girdi_toplam_kg",
    "Kilif_metre",
    "Et_fiyat_TL_kg",
    "Kuyruk_yagi_fiyat_TL_kg",
    "Baharat_fiyat_TL_kg",
    "Tuz_fiyat_TL_kg",
    "Kilif_fiyat_TL_m",
    "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_saati",
    "Iscilik_maliyeti_TL_saat",
    "Elektrik_kWh",
    "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun",
]

categorical_base = [
    "Bolge",
    "Recete_profili",
    "Isleme_modeli",
]

loss_features = [
    "Kuruma_kaybi_pct",
    "Ayiklama_fire_pct",
]

numeric_base = [c for c in numeric_base if c in df.columns]
categorical_base = [c for c in categorical_base if c in df.columns]
loss_features = [c for c in loss_features if c in df.columns]

# EKP hedefi veya üretim bittikten sonra ortaya çıkan sonuçları
# özellik olarak kullanmıyoruz.
scenarios = {
    "A_uretim_oncesi": numeric_base + categorical_base,
    "B_kayip_bilgisi_var": numeric_base + loss_features + categorical_base,
}

df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=[target]).reset_index(drop=True)
y = df[target].astype(float)

cv = KFold(n_splits=5, shuffle=True, random_state=42)
scoring = {
    "mae": "neg_mean_absolute_error",
    "rmse": "neg_root_mean_squared_error",
    "r2": "r2",
}

results = []

print("Kayit sayisi:", len(df))
print("Hedef: EKP_TL_kg")
print("Not: Sentetik veri; sonuclar gercek fabrika performansini kanitlamaz.")

for scenario_name, features in scenarios.items():
    features = list(dict.fromkeys(features))
    X = df[features].copy()

    numeric = [c for c in features if c in numeric_base or c in loss_features]
    categorical = [c for c in features if c in categorical_base]

    transformers = []
    if numeric:
        transformers.append((
            "num",
            Pipeline([("imputer", SimpleImputer(strategy="median"))]),
            numeric,
        ))
    if categorical:
        transformers.append((
            "cat",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ))

    preprocess = ColumnTransformer(transformers)

    models = {
        "RandomForest": RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            max_features=1.0,
            random_state=42,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            max_features=1.0,
            random_state=42,
            n_jobs=-1,
        ),
    }

    for model_name, estimator in models.items():
        pipe = Pipeline([
            ("preprocess", preprocess),
            ("model", estimator),
        ])
        scores = cross_validate(
            pipe, X, y, cv=cv, scoring=scoring,
            n_jobs=1, return_train_score=False,
        )
        row = {
            "Senaryo": scenario_name,
            "Model": model_name,
            "Ozellik_sayisi": len(features),
            "MAE_ortalama": -scores["test_mae"].mean(),
            "MAE_std": scores["test_mae"].std(),
            "RMSE_ortalama": -scores["test_rmse"].mean(),
            "R2_ortalama": scores["test_r2"].mean(),
        }
        results.append(row)
        print(row)

    # Referans: Her fold'da yalnızca eğitim fold'unun medyanını tahmin et.
    baseline = DummyRegressor(strategy="median")
    scores = cross_validate(
        baseline, np.zeros((len(y), 1)), y,
        cv=cv, scoring=scoring, n_jobs=1,
    )
    results.append({
        "Senaryo": scenario_name,
        "Model": "Medyan_baseline",
        "Ozellik_sayisi": 0,
        "MAE_ortalama": -scores["test_mae"].mean(),
        "MAE_std": scores["test_mae"].std(),
        "RMSE_ortalama": -scores["test_rmse"].mean(),
        "R2_ortalama": scores["test_r2"].mean(),
    })

result_df = pd.DataFrame(results).sort_values(
    ["Senaryo", "MAE_ortalama"]
)
print("\n=== SIRALAMA (MAE dusuk olan daha iyi) ===")
print(result_df.to_string(index=False))

import os
os.makedirs("reports", exist_ok=True)
result_df.to_csv(OUT, index=False, encoding="utf-8-sig")
print("\nRapor kaydedildi:", OUT)
print("Mevcut model dosyalarina dokunulmadi.")
