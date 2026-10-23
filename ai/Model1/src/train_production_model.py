"""Train a prototype production quantity regressor and compare to a baseline."""
from __future__ import annotations

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
PRODUCTION_FILE = RAW / "production_transactions_500_completed.csv"
PRODUCTS_FILE = RAW / "products.csv"
TARGET = "Produced_Quantity"
NUMERIC_FEATURES = ["Planned_Quantity", "Standard_Production_Cost", "Unit_Price", "Production_Month"]
CATEGORICAL_FEATURES = ["Product_ID", "Product_Category", "Shift", "Production_Line"]


def metrics(y_true, y_pred):
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def main() -> int:
    if not PRODUCTION_FILE.exists() or not PRODUCTS_FILE.exists():
        raise FileNotFoundError("Ham veriler yok. Önce python src/download_data.py çalıştırın.")
    production = pd.read_csv(PRODUCTION_FILE, encoding="utf-8-sig")
    products = pd.read_csv(PRODUCTS_FILE, encoding="utf-8-sig")

    needed = {"Production_ID", "Production_Date", "Product_ID", "Planned_Quantity", TARGET, "Shift", "Production_Line"}
    if not needed.issubset(production.columns):
        raise ValueError(f"Üretim CSV'sinde eksik kolonlar: {sorted(needed - set(production.columns))}")
    if not {"Product_ID", "Product_Category", "Unit_Price", "Standard_Production_Cost"}.issubset(products.columns):
        raise ValueError("products.csv dosyasında beklenen ürün/maliyet alanları eksik.")

    df = production.merge(
        products[["Product_ID", "Product_Category", "Unit_Price", "Standard_Production_Cost"]],
        on="Product_ID", how="left", validate="many_to_one"
    )
    df["Production_Date"] = pd.to_datetime(df["Production_Date"], errors="coerce")
    df["Production_Month"] = df["Production_Date"].dt.month
    for col in ["Planned_Quantity", TARGET, "Standard_Production_Cost", "Unit_Price", "Production_Month"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET, "Planned_Quantity", "Production_Date"]).copy()
    df = df[df["Planned_Quantity"] > 0].copy()
    df = df.sort_values(["Production_Date", "Production_ID"]).reset_index(drop=True)
    if len(df) < 30:
        raise ValueError(f"Model için kullanılabilir kayıt sayısı çok düşük: {len(df)}")

    # Chronological holdout: newest 20% held out; no post-production fields are predictors.
    split_at = max(1, int(len(df) * 0.8))
    train, test = df.iloc[:split_at].copy(), df.iloc[split_at:].copy()
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X_train, y_train = train[feature_cols], train[TARGET]
    X_test, y_test = test[feature_cols], test[TARGET]

    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_pipe, NUMERIC_FEATURES),
        ("cat", categorical_pipe, CATEGORICAL_FEATURES),
    ])
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=42, n_jobs=-1)),
    ])
    pipeline.fit(X_train, y_train)
    model_pred = pipeline.predict(X_test)
    # Reference method: prediction equals the planned quantity.
    baseline_pred = X_test["Planned_Quantity"].to_numpy(dtype=float)
    results = {
        "dataset": "Manufacturing_Inventory_Analytics / fan-heater manufacturing",
        "target": TARGET,
        "records_total_after_cleaning": int(len(df)),
        "train_records": int(len(train)),
        "test_records": int(len(test)),
        "train_date_range": [str(train["Production_Date"].min().date()), str(train["Production_Date"].max().date())],
        "test_date_range": [str(test["Production_Date"].min().date()), str(test["Production_Date"].max().date())],
        "features": feature_cols,
        "baseline_planned_quantity": metrics(y_test, baseline_pred),
        "random_forest": metrics(y_test, model_pred),
        "interpretation_warning": "Bu başka sektöre ait veriyle hazırlanmış prototiptir; sucuk üretimi için doğrulanmış model değildir. Model skorları çalıştırılmadan önce bilinemez.",
    }
    MODELS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": pipeline, "feature_columns": feature_cols, "target": TARGET, "trained_records": int(len(train))}, MODELS / "production_quantity_model.joblib")
    (REPORTS / "model_evaluation.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nModel: {MODELS / 'production_quantity_model.joblib'}")
    print(f"Rapor: {REPORTS / 'model_evaluation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
