from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv"
MODEL = ROOT / "models" / "ekp_model.joblib"
OUT = ROOT / "reports" / "ekp_diagnosis.json"

df = pd.read_csv(DATA)
obj = joblib.load(MODEL)

model = obj.get("model", obj.get("pipeline")) if isinstance(obj, dict) else obj
saved_features = (
    obj.get("feature_columns", obj.get("features"))
    if isinstance(obj, dict) else None
)

target = "EKP_TL_kg"

print("\n=== VERI SETI ===")
print("Kayit sayisi:", len(df))
print("Sutun sayisi:", len(df.columns))
print("EKP hedefi mevcut:", target in df.columns)
print("\nSutunlar:")
for col in df.columns:
    print(" -", col)

print("\n=== EKP DAGILIMI ===")
if target in df.columns:
    print(df[target].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]))
    print("Eksik EKP:", int(df[target].isna().sum()))
    print("Tekil EKP degeri:", int(df[target].nunique()))

print("\n=== MODELIN KULLANDIGI OZELLIKLER ===")
print("Kayitli ozellikler:", saved_features)
print("Pipeline:", type(model).__name__)

if hasattr(model, "named_steps"):
    for name, step in model.named_steps.items():
        print(f"\n{name}: {type(step).__name__}")
        if hasattr(step, "transformers_"):
            for trans_name, transformer, columns in step.transformers_:
                print(f"  {trans_name}: {list(columns) if not isinstance(columns, str) else columns}")
        if hasattr(step, "feature_importances_"):
            print("  Feature importance boyutu:", len(step.feature_importances_))

print("\n=== SAYISAL DEGISKENLERIN EKP ILE ILISKISI ===")
numeric = df.select_dtypes(include="number")
if target in numeric.columns:
    corr = numeric.corr(numeric_only=True)[target].drop(target)
    print(corr.reindex(corr.abs().sort_values(ascending=False).index).head(20))

print("\n=== OLASI HEDEF SIZINTISI KONTROLU ===")
suspicious = [
    c for c in df.columns
    if any(term in c.lower() for term in [
        "ekp", "birim_maliyet", "gercek_maliyet",
        "toplam_parti_maliyeti", "net_sucuk_ciktisi_simule"
    ])
]
print("Hedef veya sonuc bilgisini tasiyor olabilecek sutunlar:", suspicious)

result = {
    "dataset_rows": int(len(df)),
    "dataset_columns": list(df.columns),
    "target_exists": target in df.columns,
    "missing_target": int(df[target].isna().sum()) if target in df.columns else None,
    "target_summary": (
        {k: float(v) for k, v in df[target].describe().items()}
        if target in df.columns else None
    ),
    "saved_features": list(saved_features) if saved_features is not None else None,
    "suspicious_columns": suspicious,
    "note": "Diagnostic only; no model training or existing model/report overwrite."
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nAnaliz ozeti kaydedildi:", OUT)
print("Mevcut model degistirilmedi.")
