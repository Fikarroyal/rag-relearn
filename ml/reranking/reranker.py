"""Reranker linear ringan. Bobot dilatih dari hard negative (ml/training/trainer.py)."""

from __future__ import annotations
import numpy as np
from ml.common import overlap

FEATURES = ["similarity", "keyword_overlap", "is_latest", "section_match", "title_overlap"]
BASE_WEIGHTS = {"similarity": 1.0, "keyword_overlap": 0.25, "is_latest": 0.0, "section_match": 0.0, "title_overlap": 0.15}


def featurize(query: str, c: dict, latest: dict) -> np.ndarray:
    return np.array([
        c["similarity"],
        overlap(query, c["content"]),
        1.0 if c["version"] == latest.get(c["family"]) else 0.0,
        overlap(query, c.get("section", "") or ""),
        overlap(query, c.get("title", "")),
    ], dtype=np.float32)


class LinearReranker:
    def __init__(self, weights: dict | None = None, name: str = "linear-reranker"):
        self.weights = {**BASE_WEIGHTS, **(weights or {})}
        self.name = name

    @property
    def w(self):
        return np.array([self.weights[f] for f in FEATURES], dtype=np.float32)

    def rerank(self, query: str, cands: list[dict], latest: dict, version_guard: bool = False):
        out = []
        for c in cands:
            score = float(featurize(query, c, latest) @ self.w)
            if version_guard and c["version"] == latest.get(c["family"]):
                score += 0.5  # heuristik runtime dari failure detector (bukan hasil training)
            out.append({**c, "reranking_score": score})
        return sorted(out, key=lambda x: -x["reranking_score"])
