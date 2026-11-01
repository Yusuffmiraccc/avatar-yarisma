"""docs/DATA_MODEL.md ve docs/API.md dosyalarını ORM metadata ve route tablosundan üretir (kod = tek kaynak)."""
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models
from app.core.introspection import route_permissions
from app.core.permissions import ROLE_PERMISSIONS
from app.db.base import Base
from app.main import app

DOCS = Path(__file__).resolve().parents[2] / "docs"


def data_model() -> str:
    out = [
        "# Veri Modeli",
        "",
        (
            "Bu belge `backend/app/models` ORM metadata'sından üretilir (`python -m scripts.gen_docs`). "
            "İş kuralları için `README.md` ve `AI_RAPORU.md`."
        ),
        "",
        f"Toplam tablo: **{len(Base.metadata.tables)}**",
        "",
    ]
    for t in sorted(Base.metadata.tables.values(), key=lambda x: x.name):
        out += [f"## `{t.name}`", "", "| Kolon | Tip | Null | Not |", "|---|---|---|---|"]
        fks = {c.parent.name: c.target_fullname for fk in t.constraints if isinstance(fk, ForeignKeyConstraint) for c in fk.elements}
        for c in t.columns:
            notes = []
            if c.primary_key:
                notes.append("PK")
            if c.name in fks:
                notes.append(f"FK → {fks[c.name]}")
            if c.unique:
                notes.append("UNIQUE")
            out.append(f"| `{c.name}` | {str(c.type).split('(')[0] if False else c.type} | {'evet' if c.nullable else 'hayır'} | {', '.join(notes)} |")
        extras = [f"UNIQUE ({', '.join(col.name for col in k.columns)})" for k in t.constraints
                  if isinstance(k, UniqueConstraint) and len(k.columns) > 1]
        extras += [f"CHECK {k.sqltext}" for k in t.constraints if isinstance(k, CheckConstraint)]
        extras += [f"INDEX {i.name} ({', '.join(c.name for c in i.columns)})" for i in t.indexes]
        if extras:
            out += ["", "Kısıtlar/indeksler: " + "; ".join(f"`{e}`" for e in extras)]
        out.append("")
    return "\n".join(out)


def api() -> str:
    out = ["# API Özeti", "", "Üretim: `python -m scripts.gen_docs`. Ayrıntılı şema: `contract/openapi.json` ve `/api/v1/docs`.",
           "Para ve miktarlar JSON **string**; zaman UTC ISO-8601 `Z`; hata zarfı `{error:{code,message,details}, request_id}`.",
           "`Idempotency-Key` başlığı: `POST /sales`, `POST /shipments/{id}/dispatch` için zorunlu.", "",
           "## Roller ve izinler", ""]
    for role, perms in ROLE_PERMISSIONS.items():
        out.append(f"- **{role}** ({len(perms)}): " + ", ".join(f"`{p}`" for p in sorted(perms)))
    out += ["", "## Endpoint'ler", "", "| Yöntem | Yol | İzin |", "|---|---|---|"]
    for m, p, perm in route_permissions(app):
        out.append(f"| {m} | `{p}` | {perm or 'herkese açık'} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    (DOCS / "DATA_MODEL.md").write_text(data_model(), encoding="utf-8")
    (DOCS / "API.md").write_text(api(), encoding="utf-8")
    print("yazıldı: docs/DATA_MODEL.md, docs/API.md")
