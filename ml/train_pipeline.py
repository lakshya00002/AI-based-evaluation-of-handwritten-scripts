"""
Optional fine-tuning / grading calibration pipeline.

This reference script sketches how to align automated scores with human rubrics
using a small labeled dataset of (student_text, reference_text, human_score).

For production, prefer a dedicated training repo with experiment tracking (MLflow/W&B).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

# Reuse backend NLP helpers when run from repo root with PYTHONPATH=backend
try:
    from app.services import nlp_service
except ImportError:
    nlp_service = None  # type: ignore


def load_pairs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("items", [])


def featurize(row: dict[str, Any]) -> np.ndarray:
    if nlp_service is None:
        raise RuntimeError("Set PYTHONPATH to backend/ to import nlp_service.")
    sem = nlp_service.semantic_similarity(row["student_text"], row["reference_text"])
    sk, rk = nlp_service.extract_keywords_keybert(row["student_text"]), row.get("reference_keywords", [])
    if isinstance(rk, str):
        rk = [rk]
    kw = nlp_service.keyword_overlap_score(sk, rk)
    return np.array([sem, kw, sem * kw], dtype=np.float64)


def train_ridge_calibration(dataset_path: Path, out_path: Path) -> None:
    rows = load_pairs(dataset_path)
    if len(rows) < 8:
        print("Need at least 8 labeled rows for a stable split; see samples/grading_pairs.example.json")
        return
    X = np.stack([featurize(r) for r in rows])
    y = np.array([float(r["human_score"]) for r in rows])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, pred)
    print(f"Calibration Ridge MAE on holdout: {mae:.3f}")
    out = {"coef": model.coef_.tolist(), "intercept": float(model.intercept_)}
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    train_ridge_calibration(root / "samples" / "grading_pairs.example.json", root / "samples" / "calibration_weights.json")
