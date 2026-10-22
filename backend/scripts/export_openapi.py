"""OpenAPI sözleşmesini contract/openapi.json'a yazar (web ve Android DTO üretimi için tek kaynak)."""
import json
from pathlib import Path

from app.main import app

out = Path(__file__).resolve().parents[2] / "contract" / "openapi.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
print("yazıldı:", out, "-", len(app.openapi()["paths"]), "yol")
