import pandas as pd
import numpy as np

path = "data/raw/sucuk_uretim_1000_simule_parti.csv"
df = pd.read_csv(path)

def report(name, values):
    values = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) == 0:
        print(f"{name}: hesaplanamadı")
        return
    print(
        f"{name}: MAE={values.abs().mean():.6f}, "
        f"Medyan mutlak fark={values.abs().median():.6f}, "
        f"Maks mutlak fark={values.abs().max():.6f}"
    )

print("=== 1. EKP FORMUL KONTROLU ===")
required = [
    "EKP_TL_kg",
    "Toplam_parti_maliyeti_TL",
    "Net_sucuk_ciktisi_kg_simule",
]
missing = [c for c in required if c not in df.columns]
if missing:
    print("Eksik sutunlar:", missing)
else:
    calculated = (
        df["Toplam_parti_maliyeti_TL"]
        / df["Net_sucuk_ciktisi_kg_simule"].replace(0, np.nan)
    )
    report("EKP - (Toplam maliyet / net cikti)", df["EKP_TL_kg"] - calculated)

print("\n=== 2. TOPLAM MALIYET BILESENLERI ===")
components = [
    "Direkt_malzeme_toplam_TL",
    "Fason_hizmet_TL",
    "Kurum_ici_isleme_TL",
    "Paketleme_maliyeti_TL",
    "Genel_gider_TL",
]
available = [c for c in components if c in df.columns]
print("Bulunan bilesenler:", available)

if available and "Toplam_parti_maliyeti_TL" in df.columns:
    component_sum = df[available].sum(axis=1)
    report(
        "Toplam maliyet - bilesenler toplami",
        df["Toplam_parti_maliyeti_TL"] - component_sum,
    )

print("\n=== 3. MALZEME MALIYETI KONTROLU ===")
checks = [
    ("Et_maliyeti_TL", "Et_girdi_kg", "Et_fiyat_TL_kg"),
    ("Yag_maliyeti_TL", "Kuyruk_yagi_girdi_kg", "Kuyruk_yagi_fiyat_TL_kg"),
    ("Baharat_maliyeti_TL", "Baharat_girdi_kg", "Baharat_fiyat_TL_kg"),
    ("Kilif_maliyeti_TL", "Kilif_metre", "Kilif_fiyat_TL_m"),
]
for cost, qty, price in checks:
    if all(c in df.columns for c in [cost, qty, price]):
        report(cost + " - miktar*fiyat", df[cost] - df[qty] * df[price])

print("\n=== 4. EKP ILE ILISKILI DEGISKENLER ===")
cols = [
    "EKP_TL_kg",
    "Toplam_parti_maliyeti_TL",
    "Net_sucuk_ciktisi_kg_simule",
    "Karisim_girdi_toplam_kg",
    "Kuruma_kaybi_pct",
    "Ayiklama_fire_pct",
    "Et_fiyat_TL_kg",
    "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_maliyeti_TL_saat",
    "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun",
]
cols = [c for c in cols if c in df.columns]
print(df[cols].corr(numeric_only=True)["EKP_TL_kg"].sort_values().to_string())

print("\n=== 5. VERI SINIFI ===")
if "Veri_sinifi" in df.columns:
    print(df["Veri_sinifi"].value_counts(dropna=False).to_string())

print("\n=== 6. ISLEME MODELI VE KURUMA KAYBI ===")
for col in ["Isleme_modeli", "Kuruma_kaybi_pct", "Ayiklama_fire_pct"]:
    if col in df.columns:
        print(f"\n{col}:")
        if df[col].dtype == "object":
            print(df.groupby(col, dropna=False)["EKP_TL_kg"].agg(["count", "mean", "std"]).to_string())
        else:
            print(df[col].describe().to_string())

print("\nAnaliz tamamlandi. Hicbir model egitilmedi.")
