from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.models.types import utcnow


def record(db: Session, *, actor_id: int | None, action: str, entity_type: str, entity_id: int,
           details: dict | None = None, request_id: str | None = None) -> AuditEvent:
    """Aynı transaction'da yazılır: audit yazılamazsa işlem de geri alınır (fail-closed)."""
    ev = AuditEvent(actor_user_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id,
                    occurred_at=utcnow(), request_id=request_id, details=details)
    db.add(ev)
    db.flush()
    return ev
