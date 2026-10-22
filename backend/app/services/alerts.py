from sqlalchemy.orm import Session

from app.models import AnomalyAlert


def raise_alert(db: Session, *, alert_type: str, severity: str, entity_type: str, entity_id: int, message: str,
                details: dict | None = None) -> AnomalyAlert:
    a = AnomalyAlert(alert_type=alert_type, severity=severity, entity_type=entity_type, entity_id=entity_id,
                     message=message, details=details)
    db.add(a)
    db.flush()
    return a
