"""Small SQLite audit store for Model B predictions and later measurements."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import MODEL_B_AUDIT_MIGRATION

MIGRATION = MODEL_B_AUDIT_MIGRATION


class PredictionNotFound(Exception):
    pass


class ActualAlreadyExists(Exception):
    pass


class ActualNotFound(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    try:
        migration_sql = MIGRATION.read_text(encoding="utf-8")
    except OSError as exc:
        raise sqlite3.OperationalError("Model B audit migration file is missing or unreadable.") from exc
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(migration_sql)
    return connection


@contextmanager
def _connection(db_path: Path):
    connection = _connect(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def save_prediction(db_path: Path, *, bundle: dict, species: str, carcass_kg: float,
                    predicted_cuts: dict[str, float]) -> tuple[str, str]:
    prediction_id, created_at = str(uuid4()), _now()
    with _connection(db_path) as conn:
        conn.execute(
            """INSERT INTO model_b_predictions
               (prediction_id, model_version, data_version, source_type, hayvan_turu,
                karkas_agirligi_kg, predicted_cuts_kg_json, created_at_utc)
               VALUES (?, ?, ?, 'measured', ?, ?, ?, ?)""",
            (prediction_id, str(bundle["model_version"]), str(bundle["data_version"]),
             species, float(carcass_kg), json.dumps(predicted_cuts, ensure_ascii=False, allow_nan=False), created_at),
        )
    return prediction_id, created_at


def save_actual(db_path: Path, prediction_id: str, actual_cuts: dict[str, float], measured_at_utc: str) -> str:
    recorded_at = _now()
    try:
        with _connection(db_path) as conn:
            prediction = conn.execute(
                "SELECT 1 FROM model_b_predictions WHERE prediction_id = ?", (prediction_id,)
            ).fetchone()
            if prediction is None:
                raise PredictionNotFound
            existing = conn.execute(
                "SELECT 1 FROM model_b_actuals WHERE prediction_id = ?", (prediction_id,)
            ).fetchone()
            if existing is not None:
                raise ActualAlreadyExists
            conn.execute(
                """INSERT INTO model_b_actuals
                   (prediction_id, actual_cuts_kg_json, actual_source_type, measured_at_utc, recorded_at_utc)
                   VALUES (?, ?, 'measured', ?, ?)""",
                (prediction_id, json.dumps(actual_cuts, ensure_ascii=False, allow_nan=False), measured_at_utc, recorded_at),
            )
    except sqlite3.IntegrityError as exc:
        raise ActualAlreadyExists from exc
    return recorded_at


def get_evaluation(db_path: Path, prediction_id: str) -> dict:
    with _connection(db_path) as conn:
        row = conn.execute(
            """SELECT p.predicted_cuts_kg_json, p.model_version, p.data_version,
                      p.source_type, p.created_at_utc, a.actual_cuts_kg_json,
                      a.actual_source_type, a.measured_at_utc, a.recorded_at_utc
               FROM model_b_predictions p LEFT JOIN model_b_actuals a USING (prediction_id)
               WHERE p.prediction_id = ?""",
            (prediction_id,),
        ).fetchone()
    if row is None:
        raise PredictionNotFound
    if row["actual_cuts_kg_json"] is None:
        raise ActualNotFound
    predicted = json.loads(row["predicted_cuts_kg_json"])
    actual = json.loads(row["actual_cuts_kg_json"])
    return {
        "prediction_id": prediction_id,
        "model_version": row["model_version"],
        "data_version": row["data_version"],
        "source_type": row["source_type"],
        "prediction_created_at_utc": row["created_at_utc"],
        "actual_source_type": row["actual_source_type"],
        "actual_measured_at_utc": row["measured_at_utc"],
        "actual_recorded_at_utc": row["recorded_at_utc"],
        "comparison": {
            name: {
                "predicted_kg": round(float(predicted[name]), 3),
                "actual_kg": round(float(actual[name]), 3),
                "deviation_kg": round(float(predicted[name]) - float(actual[name]), 3),
            }
            for name in predicted
        },
    }
