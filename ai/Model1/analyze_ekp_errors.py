from pathlib import Path
import pandas as pd
import numpy as np

root = Path(__file__).resolve().parent
path = root / "reports" / "test_200_model_results.csv"
out = root / "reports"

df = pd.read_csv(path)

required = [
    "EKP_TL_kg",
    "predicted_ekp_tl_kg",
    "ekp_abs_error_tl_kg",
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Eksik sütunlar: {missing}")

df["ekp_signed_error_tl_kg"] = (
    df["predicted_ekp_tl_kg"] - df["EKP_TL_kg"]
)

print("\n=== GENEL HATA YÖNÜ ===")
print("Pozitif hata: model gerçek EKP'yi yüksek tahmin etti.")
print("Negatif hata: model gerçek EKP'yi düşük tahmin etti.")
print(f"Ortalama işaretli hata: {df['ekp_signed_error_tl_kg'].mean():.2f} TL/kg")
print(f"Medyan gerçek EKP: {df['EKP_TL_kg'].median():.2f} TL/kg")
print(f"Medyan tahmin EKP: {df['predicted_ekp_tl_kg'].median():.2f} TL/kg")

for col in ["Isleme_modeli", "Recete_profili", "Bolge"]:
    if col not in df.columns:
        continue

    grouped = (
        df.groupby(col, dropna=False)
        .agg(
            kayit=("EKP_TL_kg", "size"),
            gercek_ekp_ort=("EKP_TL_kg", "mean"),
            tahmin_ekp_ort=("predicted_ekp_tl_kg", "mean"),
            MAE=("ekp_abs_error_tl_kg", "mean"),
            RMSE=("ekp_abs_error_tl_kg",
                  lambda x: float(np.sqrt(np.mean(np.square(x))))),
            ort_isaretli_hata=("ekp_signed_error_tl_kg", "mean"),
        )
        .sort_values("MAE", ascending=False)
    )

    print(f"\n=== {col.upper()} GRUPLARINA GÖRE ===")
    print(grouped.round(3).to_string())

    safe_col = col.lower()
    grouped.to_csv(
        out / f"ekp_error_by_{safe_col}.csv",
        encoding="utf-8-sig"
    )

print("\n=== EN BÜYÜK 15 EKP HATASI ===")
cols = [
    c for c in [
        "test_no", "EKP_TL_kg", "predicted_ekp_tl_kg",
        "ekp_signed_error_tl_kg", "ekp_abs_error_tl_kg",
        "Et_girdi_kg", "Kuyruk_yagi_girdi_kg",
        "Baharat_girdi_kg", "Kilif_metre",
        "Isleme_modeli", "Recete_profili", "Bolge",
        "Toplam_parti_maliyeti_TL",
        "Net_sucuk_ciktisi_kg_simule",
    ] if c in df.columns
]
print(
    df.nlargest(15, "ekp_abs_error_tl_kg")[cols]
    .round(3).to_string(index=False)
)

print("\nAnaliz tamamlandı. Mevcut model dosyalarına dokunulmadı.")
