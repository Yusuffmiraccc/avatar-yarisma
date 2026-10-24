import joblib
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

from Model2.training.train_model_b import FEATURES, TARGETS, load_splits


def test_model_b_splits_are_disjoint_synthetic_and_have_expected_sizes():
    splits, _ = load_splits()
    assert {name: len(frame) for name, frame in splits.items()} == {"train": 840, "validation": 180, "test": 180}
    ids = [set(frame.kayit_id) for frame in splits.values()]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    assert all(frame.veri_kaynagi.eq("SENTETIK_SIMULASYON").all() for frame in splits.values())


def test_model_b_features_exclude_targets_and_postprocess_columns():
    assert FEATURES == ["hayvan_turu", "karkas_agirligi_kg"]
    assert not set(TARGETS) & set(FEATURES)
    assert "toplam_cikis_kg" not in FEATURES and "agirlik_dengesi_farki_kg" not in FEATURES
    assert "kayit_id" not in FEATURES


def test_model_b_default_config_points_to_sibling_model2_directory(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    ai_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.pop("MODEL_B_DIR", None)
    env.pop("MODEL_B_AUDIT_DB", None)
    env["PYTHONPATH"] = str(ai_root / "Model1")
    result = subprocess.run(
        [sys.executable, "-c", "from app.config import MODEL_B_DIR, MODEL_B_AUDIT_DB; print(MODEL_B_DIR); print(MODEL_B_AUDIT_DB)"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert Path(lines[0]) == ai_root / "Model2" / "models"
    assert Path(lines[1]) == ai_root / "Model2" / "var" / "model_b_audit.sqlite3"


def test_model_b_audit_migration_path_is_ai_rooted_and_working_directory_independent(monkeypatch, tmp_path):
    from app import model_b_audit
    expected = (model_b_audit.Path(__file__).resolve().parents[2] / "Model2" / "sql" / "001_model_b_audit.sql")
    assert model_b_audit.MIGRATION == expected
    assert model_b_audit.MIGRATION.is_file()
    monkeypatch.chdir(tmp_path)
    assert model_b_audit.MIGRATION.is_file()


def test_model_b_audit_migration_missing_has_clear_operational_error(monkeypatch, tmp_path):
    import sqlite3
    from app import model_b_audit
    monkeypatch.setattr(model_b_audit, "MIGRATION", tmp_path / "missing.sql")
    with pytest.raises(sqlite3.OperationalError, match="migration file is missing or unreadable"):
        model_b_audit._connect(tmp_path / "audit.sqlite3")


def test_candidate_artifact_manifest_records_sha256_and_synthetic_provenance():
    import hashlib
    import json
    from pathlib import Path
    candidate_path = Path(__file__).resolve().parents[2] / "Model2" / "models" / "model_b_synthetic_candidate.joblib"
    manifest_path = candidate_path.with_name("model_b_synthetic_candidate.manifest.json")
    assert candidate_path.is_file() and manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifact_sha256"] == hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    assert manifest["source_type"] == "synthetic" and manifest["production_ready"] is False


def test_model_b_loader_rejects_split_corruption(monkeypatch, tmp_path):
    import Model2.training.train_model_b as training
    monkeypatch.setattr(training, "DATA_DIR", tmp_path)
    source = pd.read_csv(training.ROOT / "data/processed/splits/ModelB_train_sentetik.csv").head(2)
    source.loc[source.index[0], "veri_kaynagi"] = "measured"
    for filename in ("ModelB_train_sentetik.csv", "ModelB_validation_sentetik.csv", "ModelB_test_sentetik.csv"):
        source.to_csv(tmp_path / filename, index=False)
    with pytest.raises(ValueError, match="sentetik olmayan"):
        training.load_splits()


def test_candidate_artifact_is_separate_and_not_production_ready(tmp_path):
    candidate = {"model": DummyRegressor(), "feature_columns": FEATURES, "target_columns": TARGETS,
                 "model_version": "test-candidate", "data_version": "model-b-synthetic-v1",
                 "source_type": "synthetic", "production_ready": False}
    path = tmp_path / "model_b_synthetic_candidate.joblib"
    joblib.dump(candidate, path)
    loaded = joblib.load(path)
    assert loaded["source_type"] == "synthetic" and loaded["production_ready"] is False
    assert path.name != "model_b_production.joblib"
