"""Fatura/irsaliye metninden alan ÖNERİSİ çıkarma (kural tabanlı) + insan onayı.

Güvence: çıkarım yalnızca öneridir; onay olmadan stok/maliyet kaydı oluşmaz. Her satır için güven puanı ve
doğrulama bayrakları üretilir. Görüntü OCR'ı sunucuda yoktur: istemci (ör. Android ML Kit) metni gönderir.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, invalid_state, not_found
from app.models import DocumentExtraction, Lot, Product, Supplier
from app.models.types import utcnow
from app.services import audit
from app.services import lots as lots_svc

UNIT_MAP = {"kg": "KG", "kilo": "KG", "g": "G", "gr": "G", "adet": "PCS", "ad": "PCS", "pcs": "PCS", "paket": "PACK",
            "pk": "PACK", "pack": "PACK"}
NUM = r"\d[\d.,]*"
LINE_RE = re.compile(
    rf"^\s*(?P<name>[^\d\n][^\n]*?)\s+(?P<qty>{NUM})\s*(?P<unit>kg|kilo|gr|g|adet|ad|pcs|paket|pk|pack)\b"
    rf"\s+(?P<price>{NUM})\s*(?:€|eur|tl|₺)?\s+(?P<total>{NUM})\s*(?:€|eur|tl|₺)?(?P<rest>.*)$",
    re.IGNORECASE,
)
LOT_RE = re.compile(r"(?:lot|parti)\s*(?:no)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_.]+)", re.IGNORECASE)
EXP_RE = re.compile(r"(?:skt|son\s*t[uü]ketim)\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4})", re.IGNORECASE)
DOCNO_RE = re.compile(r"(?:fatura|irsaliye)\s*(?:no|numaras[ıi])?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_.]+)", re.IGNORECASE)
DATE_RE = re.compile(r"(?:tarih)\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4})", re.IGNORECASE)
SUPPLIER_RE = re.compile(r"(?:sat[ıi]c[ıi]|tedarik[çc]i|firma|g[öo]nderen)\s*[:#]?\s*(.+)", re.IGNORECASE)
GRAND_RE = re.compile(rf"(?:genel\s*toplam|toplam\s*tutar|toplam)\s*[:#]?\s*({NUM})", re.IGNORECASE)


def parse_number(s: str) -> Decimal | None:
    s = s.strip().rstrip(".,")
    try:
        if "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            thou = "." if dec == "," else ","
            return Decimal(s.replace(thou, "").replace(dec, "."))
        if "," in s:
            return Decimal(s.replace(",", "."))
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):  # 1.234 → binlik
            return Decimal(s.replace(".", ""))
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_date(s: str) -> str | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9ğüşıöç ]", "", s.lower().replace("i̇", "i")).strip()


def _best(db: Session, name: str) -> tuple[Product | None, float]:
    n, best, score = _norm(name), None, 0.0
    for p in db.scalars(select(Product).where(Product.is_active.is_(True))):
        sc = max(SequenceMatcher(None, n, _norm(p.name)).ratio(), SequenceMatcher(None, n, _norm(p.code)).ratio())
        if sc > score:
            best, score = p, sc
    return (best, score) if score >= 0.6 else (None, score)


def extract(db: Session, doc_type: str, text: str) -> dict:
    warnings: list[str] = []
    docno = (DOCNO_RE.search(text) or [None, None])[1]
    dt = DATE_RE.search(text)
    doc_date = parse_date(dt.group(1)) if dt else None
    sup = None
    m = SUPPLIER_RE.search(text)
    if m:
        name = m.group(1).strip()
        n = _norm(name)
        cand = [(SequenceMatcher(None, n, _norm(s.name)).ratio(), s) for s in db.scalars(select(Supplier))]
        score, s = max(cand, key=lambda x: x[0], default=(0.0, None))
        sup = {"name_on_document": name, "matched": ({"id": s.id, "code": s.code, "name": s.name, "score": round(score, 2)}
                                                      if s and score >= 0.6 else None)}
        if sup["matched"] is None:
            warnings.append("SUPPLIER_UNMATCHED")
    lines = []
    for raw in text.splitlines():
        lm = LINE_RE.match(raw)
        if not lm:
            continue
        qty, price, total = (parse_number(lm["qty"]), parse_number(lm["price"]), parse_number(lm["total"]))
        unit = UNIT_MAP.get(lm["unit"].lower())
        prod, score = _best(db, lm["name"])
        lot = LOT_RE.search(lm["rest"] or "")
        exp = EXP_RE.search(lm["rest"] or "")
        flags = []
        if None in (qty, price, total):
            flags.append("NUMBER_PARSE_ERROR")
        elif abs(qty * price - total) > Decimal("0.01"):
            flags.append("TOTAL_MISMATCH")
        if prod is None:
            flags.append("PRODUCT_UNMATCHED")
        elif unit and unit != prod.base_unit_code:
            flags.append("UNIT_MISMATCH")
        if not lot:
            flags.append("LOT_MISSING")
        elif db.scalar(select(Lot.id).where(Lot.lot_code == lot.group(1))):
            flags.append("LOT_ALREADY_EXISTS")
        if prod is not None and prod.requires_expiry_date and not exp:
            flags.append("EXPIRY_REQUIRED_MISSING")
        conf = round(max(0.0, min(1.0, score)) * (0.5 if flags else 1.0), 2)
        lines.append({"line_index": len(lines), "text": raw.strip(), "name_on_document": lm["name"].strip(),
                      "quantity": str(qty) if qty is not None else None, "unit_code": unit,
                      "unit_cost": str(price) if price is not None else None,
                      "line_total": str(total) if total is not None else None,
                      "lot_code": lot.group(1) if lot else None,
                      "expiry_date": parse_date(exp.group(1)) if exp else None,
                      "product": ({"id": prod.id, "code": prod.code, "name": prod.name, "score": round(score, 2)}
                                  if prod else None),
                      "flags": flags, "confidence": conf})
    if not lines:
        warnings.append("NO_LINES_FOUND")
    sums = sum((Decimal(l["line_total"]) for l in lines if l["line_total"]), Decimal(0))
    gm = GRAND_RE.findall(text)
    grand = parse_number(gm[-1]) if gm else None
    if grand is not None and lines and abs(grand - sums) > Decimal("0.01"):
        warnings.append(f"GRAND_TOTAL_MISMATCH: belgede {grand}, satır toplamı {sums}")
    return {"document_number": docno, "document_date": doc_date, "supplier": sup, "lines": lines,
            "stated_total": str(grand) if grand is not None else None, "lines_total": str(sums), "warnings": warnings,
            "disclaimer": "Bu çıktı yalnızca öneridir; insan onayı olmadan kayıt oluşturulmaz."}


def create(db: Session, doc_type: str, text: str, source_name: str | None, user_id: int) -> DocumentExtraction:
    if not text.strip():
        raise bad_request("Belge metni boş.")
    doc = DocumentExtraction(doc_type=doc_type, source_name=source_name, raw_text=text[:200000],
                             proposed=extract(db, doc_type, text), status="PENDING_REVIEW", created_by=user_id)
    db.add(doc)
    db.flush()
    audit.record(db, actor_id=user_id, action="DOCUMENT_EXTRACTED", entity_type="document_extraction", entity_id=doc.id,
                 details={"lines": len(doc.proposed["lines"]), "warnings": doc.proposed["warnings"]})
    return doc


def approve(db: Session, doc_id: int, supplier_id: int | None, lines: list[dict], note: str | None, user_id: int,
            request_id: str | None) -> DocumentExtraction:
    """İnsanın düzenlediği satırlarla lot kabulleri oluşturur; hepsi tek transaction (biri hatalıysa hiçbiri)."""
    doc = db.scalar(select(DocumentExtraction).where(DocumentExtraction.id == doc_id).with_for_update())
    if doc is None:
        raise not_found("Belge", doc_id)
    if doc.status != "PENDING_REVIEW":
        raise invalid_state("Belge zaten incelenmiş.", {"status": doc.status})
    if not lines:
        raise bad_request("Onay için en az bir satır gerekir.")
    lot_ids = []
    for ln in lines:
        lot, _ = lots_svc.receive(db, lot_code=ln["lot_code"], product_id=ln["product_id"], supplier_id=supplier_id,
                                  quantity=ln["quantity"], unit_code=ln["unit_code"], unit_cost=ln["unit_cost"],
                                  received_at=None, expiry_date=ln.get("expiry_date"), user_id=user_id,
                                  request_id=request_id, source=f"document:{doc.id}")
        lot_ids.append(lot.id)
    doc.status, doc.reviewed_by, doc.reviewed_at, doc.review_note, doc.resulting_lot_ids = (
        "APPROVED", user_id, utcnow(), note, lot_ids)
    audit.record(db, actor_id=user_id, action="DOCUMENT_APPROVED", entity_type="document_extraction", entity_id=doc.id,
                 request_id=request_id, details={"lot_ids": lot_ids, "note": note})
    return doc


def reject(db: Session, doc_id: int, note: str, user_id: int) -> DocumentExtraction:
    doc = db.scalar(select(DocumentExtraction).where(DocumentExtraction.id == doc_id).with_for_update())
    if doc is None:
        raise not_found("Belge", doc_id)
    if doc.status != "PENDING_REVIEW":
        raise invalid_state("Belge zaten incelenmiş.", {"status": doc.status})
    doc.status, doc.reviewed_by, doc.reviewed_at, doc.review_note = "REJECTED", user_id, utcnow(), note
    audit.record(db, actor_id=user_id, action="DOCUMENT_REJECTED", entity_type="document_extraction", entity_id=doc.id,
                 details={"note": note})
    return doc
