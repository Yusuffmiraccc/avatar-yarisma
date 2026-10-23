"""Pure policy helpers for threshold-based retraining."""
from __future__ import annotations

import os

MIN_INITIAL_RECORDS = int(os.getenv("AVATAR_MIN_INITIAL_RECORDS", "100"))
RETRAIN_NEW_RECORDS_THRESHOLD = int(os.getenv("AVATAR_RETRAIN_NEW_RECORDS", "50"))


def should_enqueue_retraining(
    *,
    total_eligible_records: int,
    new_records_since_last_attempt: int,
    last_attempt_exists: bool,
    pending_or_running_job_exists: bool,
    active_model_exists: bool,
    min_initial_records: int = MIN_INITIAL_RECORDS,
    retrain_new_records_threshold: int = RETRAIN_NEW_RECORDS_THRESHOLD,
) -> bool:
    """Return whether the database should queue a new model-training job.

    Policy:
    - Never enqueue duplicates while a job is pending/running.
    - First training attempt requires >= min_initial_records eligible actual records.
    - After any attempt, require >= retrain_new_records_threshold newer records.
    - Data eligibility (actual + completed + validated) is enforced by the DB/API,
      not inferred from a sale or a prediction.
    """
    if pending_or_running_job_exists:
        return False
    if total_eligible_records < min_initial_records:
        return False
    if not last_attempt_exists and not active_model_exists:
        return True
    return new_records_since_last_attempt >= retrain_new_records_threshold
