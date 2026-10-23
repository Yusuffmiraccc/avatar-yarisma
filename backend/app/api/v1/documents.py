import io
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, require
from app.core.errors import AppError, not_found, request_id_of
from app.models import DocumentExtraction
from app.schemas.common import ApiModel, Dec, Page, PageParams, paginate, redact_cost_data
from app.services import documents as svc

router = APIRouter(prefix="/documents", tags=["documents"])
PP = Annotated[PageParams, Depends()]
DocType = Literal["INVOICE", "DELIVERY_NOTE"]


def _document_response(value, user, status_code: int = 200):
    content = jsonable_encoder(value) if "costs:read" in user.permissions else redact_cost_data(value)
    return JSONResponse(status_code=status_code, content=content)


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
        from pypdf.errors import PdfReadError
        if not data.startswith(b"%PDF-"):
            raise AppError(415, "UNSUPPORTED_MEDIA_TYPE", "PDF dosyasının içeriği doğrulanamadı.")
        try:
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        except (EOFError, ValueError, PdfReadError) as exc:
            raise AppError(422, "UNREADABLE_DOCUMENT", "PDF okunamadı.") from exc
        if not text.strip():
            raise AppError(422, "UNREADABLE_DOCUMENT", "PDF'de çıkarılabilir metin yok (taranmış görüntü olabilir). "
                           "İstemci tarafı OCR ile metni /documents/extract'a gönderin.")
        return text
    raise AppError(415, "UNSUPPORTED_MEDIA_TYPE", "Desteklenen dosyalar: .txt, .csv, .pdf. Görüntüler için istemci "
                   "tarafı OCR (ör. ML Kit) metnini /documents/extract'a gönderin.")


@router.post("/extract", response_model=DocumentOut, status_code=201)
def extract(body: ExtractIn, db: DB, user=require("documents:manage")):
    return _document_response(svc.create(db, body.doc_type, body.text, body.source_name, user.id), user, 201)


@router.post("/extract-file", response_model=DocumentOut, status_code=201)
async def extract_file(db: DB, file: UploadFile = File(...), doc_type: DocType = Form("INVOICE"),
                       user=require("documents:manage")):
    data = await file.read(5_000_001)
    if len(data) > 5_000_000:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "Dosya 5 MB'ı aşamaz.")
    return _document_response(svc.create(db, doc_type, _text_from_file(file.filename or "", data), file.filename, user.id), user, 201)


@router.get("", response_model=Page[DocumentOut])
def list_documents(db: DB, p: PP, status: str | None = None, user=require("documents:manage")):
    stmt = select(DocumentExtraction).order_by(DocumentExtraction.id.desc())
    if status:
        stmt = stmt.where(DocumentExtraction.status == status)
    return _document_response(paginate(db, stmt, p), user)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: DB, user=require("documents:manage")):
    doc = db.get(DocumentExtraction, doc_id)
    if doc is None:
        raise not_found("Belge", doc_id)
    return _document_response(doc, user)


@router.post("/{doc_id}/approve", response_model=DocumentOut)
def approve(doc_id: int, body: ApproveIn, request: Request, db: DB, user=require("documents:manage")):
    if "lots:receive" not in user.permissions:
        raise AppError(403, "FORBIDDEN", "Lot kabulü için yetkiniz yok.", {"required": "lots:receive"})
    result = svc.approve(db, doc_id, body.supplier_id, [l.model_dump() for l in body.lines], body.note, user.id,
                         request_id_of(request))
    return _document_response(result, user)


@router.post("/{doc_id}/reject", response_model=DocumentOut)
def reject(doc_id: int, body: RejectIn, db: DB, user=require("documents:manage")):
    return _document_response(svc.reject(db, doc_id, body.note, user.id), user)
