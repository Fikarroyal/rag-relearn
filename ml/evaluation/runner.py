"""Batch evaluation: menjalankan pipeline atas dataset evaluasi dan mendeteksi kegagalan."""

from __future__ import annotations
from ml.pipeline import run_rag
from ml.failure_detection.detector import detect
from ml.evaluation.metrics import evaluate_record, aggregate


def run_batch(dataset: list[dict], store, weights=None, top_k=5, use_reranker=True, version_guard=False, model_version="v1", llm=None):
    rows, records = [], []
    for item in dataset:
        rec = run_rag(item["query"], store, weights=weights, top_k=top_k, use_reranker=use_reranker, version_guard=version_guard,
                      ground_truth_chunk=item["ground_truth_chunk"], model_version=model_version, llm=llm)
        rec["ground_truth"] = item.get("ground_truth")
        rec["eval"] = evaluate_record(rec)
        rec["diagnosis"] = detect(rec)
        rows.append(rec["eval"])
        records.append(rec)
    agg = aggregate(rows)
    fails = [r for r in records if r["diagnosis"]]
    agg["failure_rate"] = round(len(fails) / max(len(records), 1), 4)
    return {"metrics": agg, "records": records}
