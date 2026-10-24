"""Poll the MySQL job queue and retrain only when the configured record threshold is met."""
from __future__ import annotations

import argparse
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text

from src.avatar_model import ROOT, save_candidate, train_candidate
from src.db import get_engine
from src.retraining_queue import ensure_retraining_job

RECORD_QUERY = """
SELECT production_order_id, production_date, recipe_variant, meat_kg, spice_kg, casing_kg,
       package_weight_kg, planned_material_cost_eur, planned_service_cost_eur, actual_package_count
FROM ai_production_training_records
WHERE production_status='completed' AND validation_status='validated' AND data_source='actual'
ORDER BY production_date ASC, production_order_id ASC
"""


def claim_one_job(engine):
    # Run a single worker process per database. The row lock prevents two workers from
    # claiming the same job under ordinary MySQL InnoDB transaction semantics.
    with engine.begin() as conn:
        job = conn.execute(text("""
            SELECT job_id, trigger_reason, records_total, new_records_since_attempt
            FROM ai_retraining_jobs WHERE status='pending' ORDER BY job_id ASC LIMIT 1 FOR UPDATE
        """)).mappings().first()
        if not job:
            return None
        conn.execute(text("UPDATE ai_retraining_jobs SET status='running', started_at=UTC_TIMESTAMP(6) WHERE job_id=:job_id AND status='pending'"), {"job_id": job["job_id"]})
        return dict(job)


def _active_model(engine):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT model_version, artifact_path, algorithm, metrics_json FROM ai_model_registry WHERE is_active=1 ORDER BY activated_at DESC LIMIT 1")).mappings().first()
    if not row:
        return None, None
    path = (ROOT / str(row["artifact_path"])).resolve()
    if ROOT not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Aktif modelin dosyası bulunamadı: {path}")
    return dict(row), joblib.load(path)


def process_job(engine, job: dict) -> dict:
    try:
        with engine.connect() as conn:
            records = pd.read_sql(text(RECORD_QUERY), conn)
        active_row, active_bundle = _active_model(engine)
        result = train_candidate(records, incumbent_bundle=active_bundle)
        if not result.promoted or result.model_bundle is None or result.model_version is None:
            result_doc = {"outcome": "rejected", "reason": result.reason, "algorithm": result.algorithm, **result.metrics}
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE ai_retraining_jobs SET status='rejected', finished_at=UTC_TIMESTAMP(6),
                    metrics_json=:metrics, error_message=:reason WHERE job_id=:job_id
                """), {"job_id": job["job_id"], "metrics": json.dumps(result_doc, ensure_ascii=False), "reason": result.reason[:2000]})
            print(f"Job #{job['job_id']} reddedildi: {result.reason}")
            return result_doc

        artifact_path = save_candidate(result.model_bundle)
        relative_artifact = artifact_path.relative_to(ROOT).as_posix()
        metrics_json = json.dumps(result.metrics, ensure_ascii=False)
        with engine.begin() as conn:
            # Publish atomically in the registry: at most one active model after commit.
            conn.execute(text("UPDATE ai_model_registry SET is_active=0 WHERE is_active=1"))
            conn.execute(text("""
                INSERT INTO ai_model_registry
                    (model_version, artifact_path, algorithm, trained_record_count, trained_until,
                     metrics_json, is_active, activated_at, created_at)
                VALUES
                    (:version, :artifact, :algorithm, :record_count, :trained_until,
                     :metrics, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))
            """), {
                "version": result.model_version,
                "artifact": relative_artifact,
                "algorithm": result.algorithm,
                "record_count": result.model_bundle["trained_records"],
                "trained_until": result.model_bundle["trained_through_date"],
                "metrics": metrics_json,
            })
            conn.execute(text("""
                UPDATE ai_retraining_state
                SET last_successful_training_at=UTC_TIMESTAMP(6),
                    total_records_at_last_success=:count,
                    active_model_version=:version,
                    updated_at=UTC_TIMESTAMP(6)
                WHERE singleton_id=1
            """), {"count": result.model_bundle["trained_records"], "version": result.model_version})
            conn.execute(text("""
                UPDATE ai_retraining_jobs SET status='promoted', model_version=:version,
                    finished_at=UTC_TIMESTAMP(6), metrics_json=:metrics, error_message=NULL
                WHERE job_id=:job_id
            """), {"version": result.model_version, "metrics": metrics_json, "job_id": job["job_id"]})
        result_doc = {"outcome": "promoted", "model_version": result.model_version, "artifact_path": relative_artifact, "algorithm": result.algorithm, **result.metrics}
        print(f"Job #{job['job_id']} yayınlandı: {result.model_version} ({relative_artifact})")
        return result_doc
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        with engine.begin() as conn:
            conn.execute(text("UPDATE ai_retraining_jobs SET status='failed', finished_at=UTC_TIMESTAMP(6), error_message=:error WHERE job_id=:job_id"), {"error": error[:4000], "job_id": job["job_id"]})
        print(f"Job #{job['job_id']} başarısız: {error}")
        return {"outcome": "failed", "error": error}


def main() -> int:
    parser = argparse.ArgumentParser(description="AVATAR Model 1 otomatik yeniden eğitim işçisi")
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Kuyruk kontrol aralığı (saniye)")
    parser.add_argument("--once", action="store_true", help="Bir kuyruk kontrolü yapıp çık")
    args = parser.parse_args()
    engine = get_engine()
    print(f"AVATAR retraining worker çalışıyor; poll={args.poll_seconds}s")
    try:
        while True:
            # Re-check on every idle cycle too: a threshold may have been reached while
            # another model-training job was still running.
            if not args.once:
                ensure_retraining_job(engine)
            job = claim_one_job(engine)
            if job:
                process_job(engine, job)
            elif args.once:
                print("Bekleyen eğitim işi yok.")
                return 0
            if args.once:
                return 0
            time.sleep(max(1.0, args.poll_seconds))
    except KeyboardInterrupt:
        print("Worker durduruldu.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
