"""Download raw CSV files from the selected public GitHub repository."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
BASE = "https://raw.githubusercontent.com/aftab-alam-data/Manufacturing_Inventory_Analytics/main/01_Raw_Data/"
FILES = {
    "production_transactions_500_completed.csv": "production_transactions_500_completed.csv",
    "products.csv": "products.csv",
    "bill_of_materials.csv": "bill%20of%20materials.csv",
    "raw_materials.csv": "raw%20materials.csv",
    "purchase_transactions_700_completed.csv": "purchase_transactions_700_completed.csv",
}


def download_one(session: requests.Session, filename: str, remote_name: str) -> None:
    url = BASE + remote_name
    destination = RAW_DIR / filename
    last_error = None
    for attempt in range(1, 4):
        try:
            response = session.get(url, timeout=(15, 60))
            response.raise_for_status()
            content = response.content
            if not content or content.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                raise ValueError("Sunucudan CSV yerine boş içerik/HTML geldi.")
            # Read a few bytes as UTF-8-compatible CSV text before saving.
            content[:2048].decode("utf-8-sig")
            destination.write_bytes(content)
            print(f"OK  {filename} ({len(content):,} bytes)")
            return
        except (requests.RequestException, UnicodeDecodeError, ValueError) as exc:
            last_error = exc
            print(f"Deneme {attempt}/3 başarısız: {filename}: {exc}", file=sys.stderr)
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"İndirilemedi: {filename}. Son hata: {last_error}")


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "AVATAR-Model1-DataSetup/1.0"})
        for filename, remote_name in FILES.items():
            try:
                download_one(session, filename, remote_name)
            except RuntimeError as exc:
                failures.append(str(exc))
    if failures:
        print("\nBazı dosyalar indirilemedi:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        print("İnternet bağlantısını kontrol edin. CSV bağlantıları README_TR.md içinde de var.", file=sys.stderr)
        return 1
    print(f"\nTamamlandı. Dosyalar: {RAW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
