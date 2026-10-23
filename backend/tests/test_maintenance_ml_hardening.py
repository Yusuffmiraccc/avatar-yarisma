import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Lock

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, select

from app.core.config import Settings
from app.main import create_app
from app.ml import modeling
from app.ml import service as ml_service
from app.models import AnomalyAlert, IdempotencyRecord, Lot, LotGenealogyEdge, RefreshSession, User
from app.models.types import utcnow
from scripts import purge as purge_script


def test_production_app_hides_openapi_and_docs():
    cfg = Settings(environment="production", jwt_secret_key=SecretStr("s" * 40),
                   database_url="mysql+pymysql://app:secure-pass@localhost:3306/db",
                   redis_url=SecretStr("redis://:secure-redis-pass@localhost:6379/0"))
    client = TestClient(create_app(cfg))
    assert client.get("/api/v1/openapi.json").status_code == 404
    assert client.get("/api/v1/docs").status_code == 404
    assert client.get("/api/v1/redoc").status_code == 404


def test_purge_removes_only_expired_idempotency_and_complete_refresh_families(db):
    now = utcnow()
    user_id = db.scalar(select(User.id).where(User.email == "viewer@avatar.test"))
    db.add_all([
        IdempotencyRecord(scope_key="s", idempotency_key="expired", request_hash="a", response_status=200,
                          response_body={}, created_at=now - timedelta(days=2), expires_at=now - timedelta(seconds=1)),
        IdempotencyRecord(scope_key="s", idempotency_key="valid", request_hash="b", response_status=200,
                          response_body={}, created_at=now, expires_at=now + timedelta(hours=1)),
        IdempotencyRecord(scope_key="s", idempotency_key="legacy", request_hash="c", response_status=200,
                          response_body={}, created_at=now - timedelta(days=2)),
    ])
    old = RefreshSession(user_id=user_id, family_id="expired-family", token_hash="1" * 64,
                         expires_at=now - timedelta(days=1))
    live1 = RefreshSession(user_id=user_id, family_id="live-family", token_hash="2" * 64,
                           expires_at=now - timedelta(days=1))
    live2 = RefreshSession(user_id=user_id, family_id="live-family", token_hash="3" * 64,
                           expires_at=now + timedelta(days=1))
    db.add_all([old, live1, live2])
    db.flush()
    live1.replaced_by_id = live2.id
    db.add(AnomalyAlert(alert_type="TEST", severity="INFO", entity_type="test", entity_id=1,
                        message="retain this alert", created_at=now - timedelta(days=365)))
    db.flush()

    counts = purge_script.purge(db, now=now, dry_run=True)
    assert counts == {"idempotency_records": 2, "refresh_sessions": 1}
    counts = purge_script.purge(db, now=now)
    assert counts == {"idempotency_records": 2, "refresh_sessions": 1}
    assert db.scalar(select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == "valid"))
    assert db.scalar(select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == "expired")) is None
    assert db.scalar(select(RefreshSession.id).where(RefreshSession.family_id == "expired-family")) is None
    assert len(db.scalars(select(RefreshSession).where(RefreshSession.family_id == "live-family")).all()) == 2
    assert db.scalar(select(AnomalyAlert.id).where(AnomalyAlert.message == "retain this alert")) is not None


def test_training_lock_serializes_and_model_artifacts_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(ml_service.get_settings(), "ml_dir", str(tmp_path / "artifacts"))
    active = 0
    maximum = 0
    guard = Lock()

    def run():
        nonlocal active, maximum
        with ml_service._training_lock():
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.03)
            with guard:
                active -= 1

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: run(), range(2)))
    assert maximum == 1

    path = tmp_path / "artifacts" / "round-trip.joblib"
    artifact = {"kind": "test", "version": "v1"}
    modeling.save(artifact, str(path))
    assert modeling.load(str(path)) == artifact
    assert not list(path.parent.glob("*.tmp"))


def test_traceability_forward_query_count_is_batched_for_large_fanout(db, auth, client):
    from decimal import Decimal

    from app.models import InventoryBalance

    h = auth("ADMIN")
    product_id = client.post("/api/v1/products", headers=h, json={
        "code": "QUERY-FANOUT", "name": "Query fanout", "product_type": "RAW_MATERIAL", "base_unit_code": "KG"
    }).json()["id"]
    root = Lot(lot_code="QUERY-ROOT", product_id=product_id, initial_quantity=Decimal(100), unit_code="KG",
               lot_origin_type="OPENING_STOCK", status="ACTIVE")
    db.add(root)
    db.flush()
    targets = [Lot(lot_code=f"QUERY-{n}", product_id=product_id, initial_quantity=Decimal(1), unit_code="KG",
                   lot_origin_type="PRODUCTION", status="ACTIVE") for n in range(100)]
    db.add_all(targets)
    db.flush()
    db.add_all([InventoryBalance(lot_id=lot.id, on_hand_quantity=Decimal(1)) for lot in [root, *targets]])
    db.add_all([LotGenealogyEdge(source_lot_id=root.id, target_lot_id=lot.id, process_type="REWORK", process_id=1,
                                 source_quantity=Decimal(1), source_unit_code="KG",
                                 target_quantity=Decimal(1), target_unit_code="KG") for lot in targets])
    db.flush()

    small_root = Lot(lot_code="QUERY-SMALL", product_id=product_id, initial_quantity=Decimal(2), unit_code="KG",
                     lot_origin_type="OPENING_STOCK", status="ACTIVE")
    db.add(small_root)
    db.flush()
    db.add(InventoryBalance(lot_id=small_root.id, on_hand_quantity=Decimal(2)))
    db.add_all([LotGenealogyEdge(source_lot_id=small_root.id, target_lot_id=lot.id, process_type="REWORK",
                                 process_id=1, source_quantity=Decimal(1), source_unit_code="KG",
                                 target_quantity=Decimal(1), target_unit_code="KG") for lot in targets[:2]])
    db.flush()

    statements = []
    bind = db.get_bind()

    def track(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(bind, "before_cursor_execute", track)
    try:
        from app.services.traceability import forward
        small_result = forward(db, [small_root.id])
        small_query_count = len(statements)
        statements.clear()
        result = forward(db, [root.id])
    finally:
        event.remove(bind, "before_cursor_execute", track)
    assert len(result.lots) == 101
    assert len(small_result.lots) == 3
    assert small_query_count == 9
    assert len(statements) == small_query_count


def test_model_artifact_signature_is_verified_on_load(tmp_path):
    import pytest

    from app.ml import modeling

    path = tmp_path / "m.joblib"
    modeling.save({"a": 1}, str(path))
    assert modeling.load(str(path)) == {"a": 1}
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ValueError):
        modeling.load(str(path))
    path.with_name("m.joblib.sig").unlink()
    with pytest.raises(ValueError):
        modeling.load(str(path))


def test_worse_candidate_does_not_replace_active_model(tmp_path, monkeypatch):
    from app.ml import modeling, service

    monkeypatch.setattr(service, "_dir", lambda: tmp_path)

    def art(pct):
        return {"kind": "k", "version": str(pct), "trained_at": "t", "n_samples": 1, "model_name": "m",
                "limitations": [], "metrics": {"cross_validation": {"improvement_over_baseline_percent": {"mae": pct}}}}

    assert service._promote("production_yield", art(30))["version"] == "30"
    kept = service._promote("production_yield", art(10))
    assert kept["version"] == "30" and "candidate_rejected" in kept
    assert service._promote("production_yield", art(40))["version"] == "40"
    assert modeling.load(str(tmp_path / service.KIND_FILE["production_yield"]))["version"] == "40"
