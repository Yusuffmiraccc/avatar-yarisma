from pathlib import Path
import hashlib
import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

ROOT = Path.cwd()
DATA = ROOT / "data" / "raw" / "sucuk_uretim_1000_simule_parti.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
YIELD_MODEL = MODEL_DIR / "yield_model.joblib"
EKP_MODEL = MODEL_DIR / "ekp_model.joblib"

FEATURES = [
    "Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg",
    "Tuz_girdi_kg", "Diger_kucuk_girdi_kg", "Kilif_metre",
    "Et_fiyat_TL_kg", "Kuyruk_yagi_fiyat_TL_kg",
    "Baharat_fiyat_TL_kg", "Tuz_fiyat_TL_kg",
    "Kilif_fiyat_TL_m", "Fason_birim_bedel_TL_kg_girdi",
    "Iscilik_maliyeti_TL_saat", "Elektrik_fiyati_TL_kWh",
    "Ambalaj_TL_kg_net_urun", "Bolge", "Recete_profili",
    "Isleme_modeli",
]
YIELD_TARGET = "Net_sucuk_ciktisi_kg_simule"
EKP_TARGET = "EKP_TL_kg"
COST_TARGET = "Toplam_parti_maliyeti_TL"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def unwrap_model(path):
    obj = joblib.load(path)
    if isinstance(obj, dict) and "model" in obj:
        model = obj["model"]
        columns = obj.get("feature_columns", FEATURES)
    else:
        model = obj
        columns = FEATURES
    return model, list(columns)


def evaluate(y_true, y_pred, baseline):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    base_mae = float(mean_absolute_error(y_true, np.full(len(y_true), baseline)))
    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else None,
        "baseline_MAE": base_mae,
        "baseline_improvement_pct": (
            float(100 * (1 - mae / base_mae)) if base_mae else None
        ),
    }


def main():
    for path in (DATA, YIELD_MODEL, EKP_MODEL):
        if not path.is_file():
            raise FileNotFoundError(f"Gerekli dosya bulunamadı: {path}")

    before_hashes = {
        p.name: sha256(p) for p in (YIELD_MODEL, EKP_MODEL)
    }

    df = pd.read_csv(DATA).replace([np.inf, -np.inf], np.nan)
    missing = sorted(set(FEATURES + [YIELD_TARGET, EKP_TARGET, COST_TARGET]) - set(df.columns))
    if missing:
        raise ValueError(f"Veri setinde eksik sütunlar var: {missing}")

    df = df.dropna(subset=[YIELD_TARGET, EKP_TARGET]).reset_index(drop=True)
    train_idx, test_idx = train_test_split(
        np.arange(len(df)), test_size=0.2, random_state=42
    )
    train = df.iloc[train_idx]
    test = df.iloc[test_idx].iloc[:10].copy()

    yield_model, yield_features = unwrap_model(YIELD_MODEL)
    ekp_model, ekp_features = unwrap_model(EKP_MODEL)

    for col in set(yield_features + ekp_features):
        if col not in test.columns:
            raise ValueError(f"Modelin beklediği sütun veri setinde yok: {col}")

    yield_pred = np.asarray(yield_model.predict(test[yield_features])).reshape(-1)
    ekp_pred = np.asarray(ekp_model.predict(test[ekp_features])).reshape(-1)

    actual_yield = test[YIELD_TARGET].to_numpy(dtype=float)
    actual_ekp = test[EKP_TARGET].to_numpy(dtype=float)

    rows = []
    for i, (_, row) in enumerate(test.iterrows()):
        y_abs = abs(float(yield_pred[i] - actual_yield[i]))
        e_abs = abs(float(ekp_pred[i] - actual_ekp[i]))
        y_pct = 100 * y_abs / abs(actual_yield[i]) if actual_yield[i] != 0 else None
        e_pct = 100 * e_abs / abs(actual_ekp[i]) if actual_ekp[i] != 0 else None

        rows.append({
            "test_no": i + 1,
            "source_row_index": int(test.index[i]),
            "actual_yield_kg": float(actual_yield[i]),
            "predicted_yield_kg": float(yield_pred[i]),
            "yield_abs_error_kg": y_abs,
            "yield_abs_pct_error": y_pct,
            "yield_closeness_pct": max(0.0, 100.0 - y_pct) if y_pct is not None else None,
            "actual_ekp_tl_kg": float(actual_ekp[i]),
            "predicted_ekp_tl_kg": float(ekp_pred[i]),
            "ekp_abs_error_tl_kg": e_abs,
            "ekp_abs_pct_error": e_pct,
            "ekp_closeness_pct": max(0.0, 100.0 - e_pct) if e_pct is not None else None,
        })

    results = pd.DataFrame(rows)
    metrics = {
        "yield_10_record_test": evaluate(
            actual_yield, yield_pred, float(train[YIELD_TARGET].mean())
        ),
        "ekp_10_record_test": evaluate(
            actual_ekp, ekp_pred, float(train[EKP_TARGET].mean())
        ),
        "notes": [
            "Veri setindeki kayıtların tamamı simüle edilmiştir.",
            "10 kayıtlık metrikler küçük örneklem nedeniyle kararsız olabilir.",
            "Uyum yüzdesi = max(0, 100 - mutlak yüzde hata); sınıflandırma doğruluğu değildir.",
            "R2 bu 10 kayıt üzerinde hesaplanır; tek başına üretim uygunluğu kanıtlamaz.",
            "Model dosyaları yeniden eğitilmemiştir."
        ]
    }

    REPORT_DIR.mkdir(exist_ok=True)
    csv_path = REPORT_DIR / "test_10_model_results.csv"
    json_path = REPORT_DIR / "test_10_model_results.json"
    results.to_csv(csv_path, index=False, encoding="utf-8-sig")

    after_hashes = {p.name: sha256(p) for p in (YIELD_MODEL, EKP_MODEL)}
    integrity = {
        name: {
            "before": before_hashes[name],
            "after": after_hashes[name],
            "unchanged": before_hashes[name] == after_hashes[name],
        }
        for name in before_hashes
    }
    metrics["model_file_integrity"] = integrity
    metrics["records_tested"] = len(results)
    metrics["dataset"] = str(DATA.relative_to(ROOT))
    metrics["selection"] = "train_test_split(test_size=0.2, random_state=42); ilk 10 test kaydı"
    metrics["csv_report"] = str(csv_path)
    metrics["json_report"] = str(json_path)

    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)
    print("\n=== 10 KAYITLIK TAHMİN SONUÇLARI ===")
    print(results.round(3).to_string(index=False))
    print("\n=== TOPLU METRİKLER ===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("\n=== DOSYA BÜTÜNLÜĞÜ ===")
    for name, info in integrity.items():
        print(f"{name}: {'DEĞİŞMEDİ' if info['unchanged'] else 'UYARI: HASH DEĞİŞTİ'}")
    print(f"\nCSV raporu: {csv_path}")
    print(f"JSON raporu: {json_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nTEST BAŞARISIZ: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
