"""Shared MySQL queue logic used by both the record API and the background worker."""
from __future__ import annotations

from sqlalchemy import text

from src.retraining_policy import MIN_INITIAL_RECORDS, RETRAIN_NEW_RECORDS_THRESHOLD, should_enqueue_retraining


def enqueue_if_due(conn) -> dict:
    """Within the caller's transaction, check thresholds and queue at most one job."""
    state = conn.execute(text(
        "SELECT last_attempted_at FROM ai_retraining_state WHERE singleton_id=1 FOR UPDATE"
    )).mappings().first()
    if state is None:
        raise RuntimeError("ai_retraining_state seed row eksik; sql/001_ai_tables_mysql.sql çalıştırılmalı.")

    total = int(conn.execute(text("""
        SELECT COUNT(*) FROM ai_production_training_records
        WHERE production_status='completed' AND validation_status='validated' AND data_source='actual'
    """)).scalar_one())
    last_attempt = state["last_attempted_at"]
    if last_attempt is None:
        new_since_attempt = total
    else:
        new_since_attempt = int(conn.execute(text("""
            SELECT COUNT(*) FROM ai_production_training_records
            WHERE production_status='completed' AND validation_status='validated' AND data_source='actual'
              AND recorded_at > :last_attempt
        """), {"last_attempt": last_attempt}).scalar_one())

    active_model_exists = bool(conn.execute(text(
        "SELECT EXISTS(SELECT 1 FROM ai_model_registry WHERE is_active=1)"
    )).scalar_one())
    pending = bool(conn.execute(text(
        "SELECT EXISTS(SELECT 1 FROM ai_retraining_jobs WHERE status IN ('pending','running'))"
    )).scalar_one())

    due = should_enqueue_retraining(
        total_eligible_records=total,
        new_records_since_last_attempt=new_since_attempt,
        last_attempt_exists=last_attempt is not None,
        pending_or_running_job_exists=pending,
        active_model_exists=active_model_exists,
    )
    if due:
        reason = "initial_training_threshold_reached" if not active_model_exists else "new_validated_records_threshold_reached"
        conn.execute(text("""
            INSERT INTO ai_retraining_jobs (status, trigger_reason, records_total, new_records_since_attempt, created_at)
            VALUES ('pending', :reason, :total, :new_count, UTC_TIMESTAMP(6))
        """), {"reason": reason, "total": total, "new_count": new_since_attempt})
        # This timestamp is the watermark for the next batch; it is committed atomically with the job.
        conn.execute(text("""
            UPDATE ai_retraining_state
            SET last_attempted_at=UTC_TIMESTAMP(6), updated_at=UTC_TIMESTAMP(6)
            WHERE singleton_id=1
        """))
    return {
        "enqueued": due,
        "eligible_actual_records": total,
        "new_records_since_last_attempt": new_since_attempt,
        "initial_training_threshold": MIN_INITIAL_RECORDS,
        "retraining_after_new_records": RETRAIN_NEW_RECORDS_THRESHOLD,
    }


def ensure_retraining_job(engine) -> dict:
    """Worker-side threshold check so records received while training was busy aren't missed."""
    with engine.begin() as conn:
        return enqueue_if_due(conn)
