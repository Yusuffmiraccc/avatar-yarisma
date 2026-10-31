"""Backward-compatible entry point for the reproducible Model B pipeline.

Run from the ``ai`` repository directory with:
    python -m Model2.training.ModelB_egitim_kodu
"""
from pathlib import Path
import sys

REPO_AI_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_AI_ROOT))

from Model2.training.train_model_b import main


if __name__ == "__main__":
    main()
