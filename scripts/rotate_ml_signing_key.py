"""Güvenli ML İmzalama Anahtarı Döndürme (Key Rotation) ve Doğrulama Scripti.

Kullanım:
    OLD_ML_SIGNING_SECRET="eski_anahtar" NEW_ML_SIGNING_SECRET="yeni_en_az_32_karakter_anahtar" python scripts/rotate_ml_signing_key.py

İlkeler:
1. Eski imza eski anahtarla doğrulanmadan dosya ASLA yeni anahtarla tekrar imzalanmaz.
2. Dosya içerikleri deserialize edilmez (pickle çalıştırılmaz); yalnızca bayt bütünlüğü taranır.
3. Tahrif edilmiş veya geçersiz imzalı artefaktlar derhal karantinaya alınır.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path


def rotate_signatures(artifacts_dir: Path, old_key: bytes, new_key: bytes) -> dict[str, str]:
    if not old_key or not new_key:
        raise ValueError("Hem eski hem yeni imzalama anahtarı sağlanmalıdır.")
    if old_key == new_key:
        raise ValueError("Eski ve yeni anahtarlar aynı olamaz.")
    if len(new_key) < 32:
        raise ValueError("Yeni ML_SIGNING_SECRET en az 32 karakter olmalıdır.")

    results: dict[str, str] = {}
    joblib_files = list(artifacts_dir.glob("*.joblib"))
    if not joblib_files:
        print(f"Bilgi: '{artifacts_dir}' dizininde hiçbir .joblib modeli bulunamadı.")
        return results

    for model_path in joblib_files:
        sig_path = model_path.with_name(f"{model_path.name}.sig")
        if not sig_path.exists():
            results[model_path.name] = "REDDEDİLDİ: .sig dosyası eksik"
            print(f"[HATA] {model_path.name}: İmza dosyası bulunamadı; yeniden imzalama reddedildi.")
            continue

        raw_bytes = model_path.read_bytes()
        existing_sig = sig_path.read_text().strip()
        expected_old_sig = hmac.new(old_key, raw_bytes, hashlib.sha256).hexdigest()

        # 1. Eski anahtarla doğrulama (Sabit zamanlı karşılaştırma)
        if not hmac.compare_digest(existing_sig, expected_old_sig):
            results[model_path.name] = "REDDEDİLDİ: Eski imza uyuşmuyor (tahrif edilmiş olabilir)"
            print(f"[GÜVENLİK UYARISI] {model_path.name}: Mevcut imza eski anahtarla eşleşmiyor! İşlem durduruldu.")
            continue

        # 2. Yeni anahtarla imza üretme ve atomik yazma
        new_sig = hmac.new(new_key, raw_bytes, hashlib.sha256).hexdigest()
        tmp_sig_path = sig_path.with_suffix(".sig.tmp")
        tmp_sig_path.write_text(new_sig)
        os.replace(tmp_sig_path, sig_path)
        results[model_path.name] = "BAŞARILI: Yeni anahtarla yeniden imzalandı"
        print(f"[BAŞARILI] {model_path.name}: Güvenle yeni anahtara geçirildi.")

    return results


def main() -> int:
    old_secret = os.environ.get("OLD_ML_SIGNING_SECRET", "").encode("utf-8")
    new_secret = os.environ.get("NEW_ML_SIGNING_SECRET", "").encode("utf-8")
    artifacts_dir = Path(os.environ.get("ML_DIR", "ml_artifacts"))
    if not artifacts_dir.is_absolute():
        artifacts_dir = Path("backend") / artifacts_dir

    if not old_secret or not new_secret:
        print("Hata: OLD_ML_SIGNING_SECRET ve NEW_ML_SIGNING_SECRET çevre değişkenleri tanımlanmalıdır.")
        return 1

    try:
        results = rotate_signatures(artifacts_dir, old_secret, new_secret)
        print("Anahtar Döndürme Özeti:", results)
        return 0 if all("BAŞARILI" in v for v in results.values()) else 2
    except Exception as e:
        print(f"Kritik Hata: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
