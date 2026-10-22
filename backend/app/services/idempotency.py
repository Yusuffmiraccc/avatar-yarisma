import hashlib
import json
from collections.abc import Callable

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.models import IdempotencyRecord


def request_hash(body: BaseModel | dict) -> str:
    data = body.model_dump(mode="json") if isinstance(body, BaseModel) else body
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(db: Session, *, scope: str, key: str | None, body: BaseModel | dict, required: bool,
        action: Callable[[], tuple[int, BaseModel]]) -> JSONResponse:
    """Aynı anahtar+aynı gövde → ilk yanıt; aynı anahtar+farklı gövde → 409 IDEMPOTENCY_KEY_REUSED."""
    if not key:
        if required:
            raise bad_request("Idempotency-Key başlığı zorunludur.", {"header": "Idempotency-Key"})
        status, result = action()
        return JSONResponse(status_code=status, content=result.model_dump(mode="json"))
    if len(key) > 128:
        raise bad_request("Idempotency-Key en fazla 128 karakter olabilir.")
    h = request_hash(body)

    def existing() -> IdempotencyRecord | None:
        return db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.scope_key == scope,
                                                         IdempotencyRecord.idempotency_key == key))

    def replay(rec: IdempotencyRecord) -> JSONResponse:
        if rec.request_hash != h:
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED", "Bu anahtar farklı bir istek gövdesiyle kullanılmış.")
        return JSONResponse(status_code=rec.response_status, content=rec.response_body,
                            headers={"Idempotent-Replay": "true"})

    rec = existing()
    if rec is not None:
        return replay(rec)
    # Yer tutucu satır: eşzamanlı aynı anahtar, bu transaction bitene kadar unique indekste bekler;
    # commit olursa IntegrityError → kayıtlı yanıt tekrar verilir, rollback olursa ikinci istek çalışır.
    placeholder = IdempotencyRecord(scope_key=scope, idempotency_key=key, request_hash=h, response_status=0,
                                    response_body={})
    try:
        with db.begin_nested():
            db.add(placeholder)
            db.flush()
    except IntegrityError:
        rec = existing()
        if rec is None:
            raise AppError(409, "CONFLICT", "Aynı anahtarlı istek eşzamanlı işleniyor; tekrar deneyin.")
        return replay(rec)
    status, result = action()
    content = result.model_dump(mode="json")
    placeholder.response_status, placeholder.response_body = status, content
    db.flush()
    return JSONResponse(status_code=status, content=content)
