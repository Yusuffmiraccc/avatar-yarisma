"""Purge expired replay/refresh state without touching operational or audit records.

Idempotency responses are retained for 24 hours. Legacy rows with no expires_at use
created_at plus that same retention interval. Refresh rows are deleted by family only
after every token in the family has expired, preserving rotation/reuse history while any
family token can still be used. Anomaly alerts, audit events, and ML predictions are
retained; this command intentionally has no alert-deletion option.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Direct script execution from backend/.

from app.db.session import SessionLocal
from app.models import IdempotencyRecord, RefreshSession
from app.models.types import utcnow
from app.services.idempotency import IDEMPOTENCY_RETENTION

FAMILY_BATCH_SIZE = 500


def purge(db: Session, *, now=None, dry_run: bool = False) -> dict[str, int]:
    now = now or utcnow()
    cutoff = now - IDEMPOTENCY_RETENTION
    idem_expired = ((IdempotencyRecord.expires_at.is_not(None)) & (IdempotencyRecord.expires_at <= now)) | (
        IdempotencyRecord.expires_at.is_(None) & (IdempotencyRecord.created_at <= cutoff))
    idempotency_count = db.scalar(select(func.count()).select_from(IdempotencyRecord).where(idem_expired)) or 0
    expired_families = (select(RefreshSession.family_id)
                        .group_by(RefreshSession.family_id)
                        .having(func.max(RefreshSession.expires_at) <= now))
    refresh_count = db.scalar(select(func.count()).select_from(RefreshSession).where(
        RefreshSession.family_id.in_(expired_families))) or 0
    result = {"idempotency_records": idempotency_count, "refresh_sessions": refresh_count}
    if dry_run:
        return result

    db.execute(delete(IdempotencyRecord).where(idem_expired))
    removed_refresh = 0
    while True:
        families = list(db.scalars(expired_families.limit(FAMILY_BATCH_SIZE)))
        if not families:
            break
        # Clear self-references first so FK enforcement remains enabled during deletion.
        db.execute(update(RefreshSession).where(RefreshSession.family_id.in_(families))
                   .values(replaced_by_id=None))
        deleted = db.execute(delete(RefreshSession).where(RefreshSession.family_id.in_(families)))
        removed_refresh += deleted.rowcount or 0
    result["refresh_sessions"] = removed_refresh
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show eligible row counts without deleting")
    args = parser.parse_args()
    with SessionLocal() as db, db.begin():
        counts = purge(db, dry_run=args.dry_run)
    action = "Would purge" if args.dry_run else "Purged"
    print(f"{action}: {counts['idempotency_records']} idempotency records, "
          f"{counts['refresh_sessions']} refresh sessions; anomaly/audit records retained.")


if __name__ == "__main__":
    main()
