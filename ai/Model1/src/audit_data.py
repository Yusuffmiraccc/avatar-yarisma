"""Inspect CSV schemas, quality, IDs, and create a Markdown audit report."""
from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
EXPECTED = {
    "production_transactions_500_completed.csv": {
        "Production_ID", "Production_Date", "Product_ID", "Planned_Quantity",
        "Produced_Quantity", "Rejected_Quantity", "Shift", "Production_Line",
    },
    "products.csv": {"Product_ID", "Product_Name", "Product_Category", "Unit_Price", "Standard_Production_Cost"},
    "bill_of_materials.csv": {"BOM_ID", "Product_ID", "Material_ID", "Quantity_Required", "Wastage_Percent", "BOM_Status"},
    "raw_materials.csv": {"Material_ID", "Material_Name", "Unit_of_Measure", "Standard_Unit_Cost"},
    "purchase_transactions_700_completed.csv": {"Purchase_ID", "Material_ID", "Purchase_Quantity", "Unit_Cost", "Delivery_Status"},
}


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    frames = {}
    problems = []
    lines = ["# Model 1 — Veri Denetim Raporu", "", "> Kaynak: `aftab-alam-data/Manufacturing_Inventory_Analytics`. Üretim kayıtları fan/ısıtıcı gibi ürünlere aittir. Sucuk üretimine doğrudan genellenemez.", ""]

    for filename, required in EXPECTED.items():
        path = RAW / filename
        if not path.exists():
            problems.append(f"Eksik dosya: `{filename}`. Önce `python src/download_data.py` çalıştırın.")
            continue
        try:
            df = load_csv(path)
        except Exception as exc:
            problems.append(f"`{filename}` okunamadı: {exc}")
            continue
        frames[filename] = df
        missing_cols = sorted(required - set(df.columns))
        lines += [f"## `{filename}`", "", f"- Satır: **{len(df):,}**", f"- Sütun: **{len(df.columns)}**", f"- Yinelenen satır: **{int(df.duplicated().sum()):,}**", f"- Eksik hücre sayısı: **{int(df.isna().sum().sum()):,}**", f"- Sütunlar: `{', '.join(map(str, df.columns))}`", f"- Beklenen kolon eksikleri: `{', '.join(missing_cols) if missing_cols else 'yok'}`", ""]
        if missing_cols:
            problems.append(f"`{filename}` beklenen kolonlardan yoksun: {', '.join(missing_cols)}")

    prod_name = "production_transactions_500_completed.csv"
    if prod_name in frames:
        p = frames[prod_name].copy()
        for c in ["Planned_Quantity", "Produced_Quantity", "Rejected_Quantity"]:
            p[c] = pd.to_numeric(p[c], errors="coerce")
        dates = pd.to_datetime(p["Production_Date"], errors="coerce")
        lines += ["## Üretim kayıtları — temel KPI'lar", "", f"- Benzersiz üretim ID: **{p['Production_ID'].nunique():,}**", f"- Benzersiz ürün: **{p['Product_ID'].nunique():,}**", f"- Tarih aralığı: **{dates.min()} — {dates.max()}**", f"- Planlanan toplam miktar: **{p['Planned_Quantity'].sum():,.2f}**", f"- Gerçekleşen toplam miktar: **{p['Produced_Quantity'].sum():,.2f}**", f"- Reddedilen toplam miktar: **{p['Rejected_Quantity'].sum():,.2f}**", f"- Toplam gerçekleşen / planlanan: **{p['Produced_Quantity'].sum() / p['Planned_Quantity'].sum() * 100:.2f}%**", f"- Yinelenen `Production_ID`: **{int(p['Production_ID'].duplicated().sum()):,}**", f"- Planlanan miktarı sıfır/negatif kayıtlar: **{int((p['Planned_Quantity'] <= 0).sum()):,}**", f"- Gerçek miktarı planlanan miktardan büyük kayıtlar: **{int((p['Produced_Quantity'] > p['Planned_Quantity']).sum()):,}**", ""]

    # Foreign-key checks across separate tables.
    if all(n in frames for n in [prod_name, "products.csv", "bill_of_materials.csv", "raw_materials.csv"]):
        p = frames[prod_name]
        products = frames["products.csv"]
        bom = frames["bill_of_materials.csv"]
        materials = frames["raw_materials.csv"]
        missing_products = sorted(set(p["Product_ID"].dropna()) - set(products["Product_ID"].dropna()))
        missing_bom_products = sorted(set(products["Product_ID"].dropna()) - set(bom["Product_ID"].dropna()))
        missing_materials = sorted(set(bom["Material_ID"].dropna()) - set(materials["Material_ID"].dropna()))
        lines += ["## Tablo ilişkileri", "", f"- Üretim tablosunda ürün kartında bulunmayan Product_ID: **{len(missing_products)}**", f"- BOM kaydı olmayan ürün: **{len(missing_bom_products)}**", f"- Hammadde kartında bulunmayan BOM Material_ID: **{len(missing_materials)}**", ""]
        if missing_products: problems.append(f"Ürün kartında bulunmayan Product_ID değerleri: {missing_products}")
        if missing_materials: problems.append(f"Hammadde kartında bulunmayan Material_ID değerleri: {missing_materials}")

    lines += ["## Uyarılar ve yorum", "", "- Bu veri başka bir imalat bağlamına (fan/ısıtıcı ürünleri) aittir; AVATAR sucuk üretimi için alan/dağılım eşleşmesi sağlamaz.", "- Üretim CSV'si üretim miktarını modellemeye yardımcı olabilir; üretim emri bazında gerçek toplam malzeme maliyetini ve dış hizmet faturasını doğrudan içermiyor.", "- BOM ve satın alma tabloları malzeme maliyet yapısını incelemeye yarar, fakat gerçek sucuk üretim maliyetlerinin yerine geçmez.", "- Kaynak depoda açık lisans dosyası görülmedi; yeniden dağıtım/ürünleştirme öncesinde lisansı doğrulayın.", ""]
    lines.append("## Kontrol sorunları\n")
    if problems:
        lines += [f"- ⚠️ {x}" for x in problems]
    else:
        lines.append("- Kritik dosya/şema kontrolünde sorun görünmedi. Bu, verinin sucuk üretimine uygun veya istatistiksel olarak yeterli olduğunu tek başına kanıtlamaz.")
    lines.append("")

    report = REPORTS / "data_audit.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(report.read_text(encoding="utf-8"))
    print(f"Rapor kaydedildi: {report}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
