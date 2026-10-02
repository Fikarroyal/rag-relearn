"""Metrik retrieval & generation."""

from __future__ import annotations
import math
from ml.common import overlap


def recall_at_k(ranked_ids, gt, k):
    return 1.0 if gt in ranked_ids[:k] else 0.0


def precision_at_k(ranked_ids, gt, k):
    return (1.0 if gt in ranked_ids[:k] else 0.0) / max(k, 1)


def mrr(ranked_ids, gt):
    return 1.0 / (ranked_ids.index(gt) + 1) if gt in ranked_ids else 0.0


def ndcg(ranked_ids, gt, k=10):
    return 1.0 / math.log2(ranked_ids.index(gt) + 2) if gt in ranked_ids[:k] else 0.0


def evaluate_record(rec: dict, ground_truth_text: str = "") -> dict:
    ids = [c["chunk_id"] for c in rec["reranked"]]
    gt = rec["ground_truth_chunk"]
    sel = rec["selected"]
    ctx_prec = sum(1 for c in sel if c["chunk_id"] == gt) / max(len(sel), 1)
    cited_ok = [c for c in rec["citations"] if c == gt]
    return {
        "recall@1": recall_at_k(ids, gt, 1), "recall@3": recall_at_k(ids, gt, 3), "recall@5": recall_at_k(ids, gt, 5),
        "recall@10": recall_at_k(ids, gt, 10), "precision@k": precision_at_k(ids, gt, len(ids)), "mrr": mrr(ids, gt), "ndcg": ndcg(ids, gt),
        "context_precision": ctx_prec, "context_recall": 1.0 if gt in [c["chunk_id"] for c in sel] else 0.0,
        "faithfulness": rec["metrics"]["faithfulness"], "answer_relevance": overlap(rec["query"], rec["answer"]) if rec["answer"] else 0.0,
        "citation_accuracy": (len(cited_ok) / len(rec["citations"])) if rec["citations"] else 0.0,
        "hallucination_rate": 1.0 if rec["metrics"]["faithfulness"] < 0.5 else 0.0,
        "latency_ms": rec["metrics"]["total_ms"],
    }


def aggregate(rows: list[dict]) -> dict:
    keys = rows[0].keys() if rows else []
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in keys}
