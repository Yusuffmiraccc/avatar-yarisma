import io
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import AppError, bad_request, not_found, request_id_of
from app.models import DocumentExtraction
from app.schemas.common import ApiModel, Dec, Page, PageParams, paginate
from app.services import documents as svc

router = APIRouter(prefix="/documents", tags=["documents"])
PP = Annotated[PageParams, Depends()]
DocType = Literal["INVOICE", "DELIVERY_NOTE"]


class ExtractIn(BaseModel):
    doc_type: DocType = "INVOICE"
    text: str = Field(min_length=1, max_length=200000)
    source_name: str | None = Field(default=None, max_length=200)


class ApprovedLine(BaseModel):
    product_id: int
    lot_code: str = Field(min_length=1, max_length=80)
    quantity: Dec
    unit_code: str
    unit_cost: Dec
    expiry_date: date | None = None


class ApproveIn(BaseModel):
    supplier_id: int | None = None
    lines: list[ApprovedLine] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)


class RejectIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)


class DocumentOut(ApiModel):
    id: int
    doc_type: str
    source_name: str | None = None
    status: str
    proposed: dict
    review_note: str | None = None
    resulting_lot_ids: list | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


def _text_from_file(name: str, data: bytes) -> str:
    low = name.lower()
    if low.endswith((".txt", ".csv")):
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
    if low.endswith(".pdf"):
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if not text.strip():
            raise AppError(422, "UNREADABLE_DOCUMENT", "PDF'de çıkarılabilir metin yok (taranmış görüntü olabilir). "
                           "İstemci tarafı OCR ile metni /documents/extract'a gönderin.")
        return text
    raise AppError(415, "UNSUPPORTED_MEDIA_TYPE", "Desteklenen dosyalar: .txt, .csv, .pdf. Görüntüler için istemci "
                   "tarafı OCR (ör. ML Kit) metnini /documents/extract'a gönderin.")


@router.post("/extract", response_model=DocumentOut, status_code=201)
def extract(body: ExtractIn, db: DB, user=require("documents:manage")):
    return svc.create(db, body.doc_type, body.text, body.source_name, user.id)


@router.post("/extract-file", response_model=DocumentOut, status_code=201)
async def extract_file(db: DB, file: UploadFile = File(...), doc_type: DocType = Form("INVOICE"),
                       user=require("documents:manage")):
    data = await file.read()
    if len(data) > 5_000_000:
        raise bad_request("Dosya 5 MB'ı aşamaz.")
    return svc.create(db, doc_type, _text_from_file(file.filename or "", data), file.filename, user.id)


@router.get("", response_model=Page[DocumentOut])
def list_documents(db: DB, p: PP, status: str | None = None, _=require("documents:manage")):
    stmt = select(DocumentExtraction).order_by(DocumentExtraction.id.desc())
    if status:
        stmt = stmt.where(DocumentExtraction.status == status)
    return paginate(db, stmt, p)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: DB, _=require("documents:manage")):
    doc = db.get(DocumentExtraction, doc_id)
    if doc is None:
        raise not_found("Belge", doc_id)
    return doc


@router.post("/{doc_id}/approve", response_model=DocumentOut)
def approve(doc_id: int, body: ApproveIn, request: Request, db: DB, user=require("documents:manage")):
    if "lots:receive" not in user.permissions:
        raise AppError(403, "FORBIDDEN", "Lot kabulü için yetkiniz yok.", {"required": "lots:receive"})
    return svc.approve(db, doc_id, body.supplier_id, [l.model_dump() for l in body.lines], body.note, user.id,
                       request_id_of(request))


@router.post("/{doc_id}/reject", response_model=DocumentOut)
def reject(doc_id: int, body: RejectIn, db: DB, user=require("documents:manage")):
    return svc.reject(db, doc_id, body.note, user.id)
