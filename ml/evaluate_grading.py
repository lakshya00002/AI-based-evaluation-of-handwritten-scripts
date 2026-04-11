"""
Offline evaluation: compare model scores to human scores (Pearson / Spearman / MAE).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def mae(xs: list[float], ys: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(xs, ys)) / len(xs)


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "samples" / "grading_pairs.example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = data["items"]
    human = [float(r["human_score"]) for r in rows]
    auto = [float(r.get("auto_score", r["human_score"])) for r in rows]
    print(f"MAE (auto vs human): {mae(auto, human):.3f}")
    print(f"Pearson correlation: {pearson(auto, human):.3f}")


if __name__ == "__main__":
    main()
