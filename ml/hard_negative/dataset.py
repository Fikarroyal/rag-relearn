"""Training dataset generator + quality validation + split tanpa leakage."""

from __future__ import annotations
import hashlib
import json

REQUIRED = ["query", "positive", "hard_negative", "reason", "failure_type"]


def validate(samples: list[dict], valid_chunks: set[str]) -> dict:
    issues, seen, labels = [], {}, {}
    for i, s in enumerate(samples):
        miss = [f for f in REQUIRED if not s.get(f)]
        if miss:
            issues.append({"index": i, "issue": "missing_field", "detail": miss})
        key = (s.get("query"), s.get("positive"), s.get("hard_negative"))
        if key in seen:
            issues.append({"index": i, "issue": "duplicate_sample"})
        seen[key] = i
        if s.get("positive") == s.get("hard_negative"):
            issues.append({"index": i, "issue": "contradictory_label", "detail": "positive == negative"})
        if valid_chunks and (s.get("positive") not in valid_chunks or s.get("hard_negative") not in valid_chunks):
            issues.append({"index": i, "issue": "invalid_document"})
        if s.get("quality_score", 1) < 0.4:
            issues.append({"index": i, "issue": "low_quality_negative"})
        labels.setdefault((s.get("query"), s.get("hard_negative")), set()).add(s.get("positive"))
    for (q, n), poss in labels.items():
        if n in poss:
            issues.append({"issue": "contradictory_label", "detail": f"{n} juga positif untuk '{q}'"})
    return {"ok": not issues, "issues": issues}


def split(samples: list[dict], val=0.15, test=0.15) -> list[dict]:
    """Split deterministik per-query (hash) sehingga tidak ada leakage query antar split."""
    out = []
    for s in samples:
        b = int(hashlib.md5(s["query"].encode()).hexdigest(), 16) % 100 / 100
        out.append({**s, "split": "test" if b < test else "validation" if b < test + val else "train"})
    return out


def leakage(samples: list[dict]) -> int:
    by_q: dict = {}
    for s in samples:
        by_q.setdefault(s["query"], set()).add(s["split"])
    return sum(1 for v in by_q.values() if len(v) > 1)


def to_jsonl(samples):
    return "\n".join(json.dumps(s, ensure_ascii=False) for s in samples)
