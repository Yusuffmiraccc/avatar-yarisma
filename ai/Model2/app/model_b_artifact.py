from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

import joblib

from app.schemas import MODEL_B_FEATURES, MODEL_B_TARGETS


PRODUCTION_FILENAME = "model_b_production.joblib"
PRODUCTION_MANIFEST = "model_b_production.manifest.json"
CANDIDATE_FILENAME = "model_b_synthetic_candidate.joblib"
CANDIDATE_MANIFEST = "model_b_synthetic_candidate.manifest.json"


def _sha256_fileobj(file_obj) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _read_checked_manifest(
    model_dir: Path,
    *,
    artifact_filename: str,
    manifest_filename: str,
    source_type: str,
    production_ready: bool,
) -> dict[str, Any] | None:
    artifact_path = Path(model_dir) / artifact_filename
    manifest_path = Path(model_dir) / manifest_filename
    if not artifact_path.is_file() or not manifest_path.is_file():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hash = manifest.get("artifact_sha256")
        if (
            manifest.get("production_ready") is not production_ready
            or manifest.get("source_type") != source_type
            or manifest.get("feature_columns") != list(MODEL_B_FEATURES)
            or manifest.get("target_columns") != list(MODEL_B_TARGETS)
            or not isinstance(manifest.get("model_version"), str)
            or not manifest.get("model_version")
            or not isinstance(manifest.get("data_version"), str)
            or not manifest.get("data_version")
            or not _valid_sha256(expected_hash)
        ):
            return None

        with artifact_path.open("rb") as artifact_file:
            actual_hash = _sha256_fileobj(artifact_file)
        if not secrets.compare_digest(actual_hash, expected_hash.lower()):
            return None
        return manifest
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def read_production_manifest(model_dir: Path) -> dict[str, Any] | None:
    """Read verified measured production metadata without deserializing the model."""
    return _read_checked_manifest(
        model_dir,
        artifact_filename=PRODUCTION_FILENAME,
        manifest_filename=PRODUCTION_MANIFEST,
        source_type="measured",
        production_ready=True,
    )


def read_synthetic_candidate_manifest(model_dir: Path) -> dict[str, Any] | None:
    """Read candidate metadata and hash; never unpickle the synthetic artifact."""
    return _read_checked_manifest(
        model_dir,
        artifact_filename=CANDIDATE_FILENAME,
        manifest_filename=CANDIDATE_MANIFEST,
        source_type="synthetic",
        production_ready=False,
    )


def load_production_bundle(model_dir: Path) -> dict[str, Any] | None:
    manifest = read_production_manifest(model_dir)
    if manifest is None:
        return None

    artifact_path = Path(model_dir) / PRODUCTION_FILENAME
    try:
        with artifact_path.open("rb") as artifact_file:
            actual_hash = _sha256_fileobj(artifact_file)
            if not secrets.compare_digest(actual_hash, manifest["artifact_sha256"].lower()):
                return None
            artifact_file.seek(0)
            bundle = joblib.load(artifact_file)

        if (
            not isinstance(bundle, dict)
            or bundle.get("production_ready") is not True
            or bundle.get("source_type") != "measured"
            or bundle.get("feature_columns") != list(MODEL_B_FEATURES)
            or bundle.get("target_columns") != list(MODEL_B_TARGETS)
            or not isinstance(bundle.get("model_version"), str)
            or not bundle.get("model_version")
            or not isinstance(bundle.get("data_version"), str)
            or not bundle.get("data_version")
            or not hasattr(bundle.get("model"), "predict")
            or bundle.get("model_version") != manifest["model_version"]
            or bundle.get("data_version") != manifest["data_version"]
        ):
            return None
        return bundle
    except Exception:
        return None


def load_synthetic_candidate_bundle(model_dir: Path) -> dict[str, Any] | None:
    """Load verified synthetic candidate artifact strictly for experimental pilot inference."""
    manifest = read_synthetic_candidate_manifest(model_dir)
    if manifest is None:
        return None

    artifact_path = Path(model_dir) / CANDIDATE_FILENAME
    try:
        with artifact_path.open("rb") as artifact_file:
            actual_hash = _sha256_fileobj(artifact_file)
            if not secrets.compare_digest(actual_hash, manifest["artifact_sha256"].lower()):
                return None
            artifact_file.seek(0)
            bundle = joblib.load(artifact_file)

        if (
            not isinstance(bundle, dict)
            or bundle.get("production_ready") is not False
            or bundle.get("source_type") != "synthetic"
            or bundle.get("feature_columns") != list(MODEL_B_FEATURES)
            or bundle.get("target_columns") != list(MODEL_B_TARGETS)
            or not isinstance(bundle.get("model_version"), str)
            or not bundle.get("model_version")
            or not isinstance(bundle.get("data_version"), str)
            or not bundle.get("data_version")
            or not hasattr(bundle.get("model"), "predict")
            or bundle.get("model_version") != manifest["model_version"]
            or bundle.get("data_version") != manifest["data_version"]
        ):
            return None
        return bundle
    except Exception:
        return None

