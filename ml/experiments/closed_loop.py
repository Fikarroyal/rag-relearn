"""Eksperimen closed-loop: Baseline vs +Reranker vs +Failure Detection vs RAG-Relearn (dataset evaluasi yang sama)."""

from __future__ import annotations
import json
from pathlib import Path
from ml.ingestion import chunk_document
from ml.retrieval.retriever import VectorStore
from ml.evaluation.runner import run_batch
from ml.hard_negative.miner import mine
from ml.hard_negative import dataset as ds
from ml.training.trainer import train
from ml.reranking.reranker import BASE_WEIGHTS

ROOT = Path(__file__).resolve().parents[2]
NO_ITEM = {"is_latest": 0.0, "section_match": 0.0}


def load_store(seed_dir=None) -> VectorStore:
    chunks = []
    for p in sorted((seed_dir or ROOT / "data" / "seed_docs").glob("*.md")):
        chunks += chunk_document(p)["chunks"]
    return VectorStore(chunks)


def load_eval() -> list[dict]:
    return json.loads((ROOT / "data" / "eval_dataset.json").read_text(encoding="utf-8"))


def load_train_queries() -> list[dict]:
    return json.loads((ROOT / "data" / "train_queries.json").read_text(encoding="utf-8"))


def collect_samples(records, store):
    samples = []
    for r in records:
        if not r["diagnosis"]:
            continue
        for hn in mine(r["query"], r["ground_truth_chunk"], store):
            samples.append({**hn, "failure_type": r["diagnosis"]["failure_type"]})
    return samples


def run_experiment(store=None, dataset=None, train_queries=None, epochs=40, lr=0.5) -> dict:
    store, dataset = store or load_store(), dataset or load_eval()
    arms = {
        "baseline": dict(use_reranker=False),
        "rag_reranker": dict(use_reranker=True, weights=BASE_WEIGHTS),
        "rag_failure_detection": dict(use_reranker=True, weights=BASE_WEIGHTS, version_guard=True),
    }
    results = {k: run_batch(dataset, store, **v, model_version=k) for k, v in arms.items()}
    # Training memakai query TERPISAH dari dataset evaluasi (tanpa leakage query).
    base = run_batch(train_queries or load_train_queries(), store, use_reranker=False)["records"]
    samples = ds.split(collect_samples(base, store))
    tr = [s for s in samples if s["split"] == "train"] or samples
    va = [s for s in samples if s["split"] == "validation"]
    trained = train(tr, va, store, epochs=epochs, lr=lr)
    results["rag_relearn"] = run_batch(dataset, store, weights=trained["weights"], use_reranker=True, model_version="relearn-v2")
    return {"summary": {k: v["metrics"] for k, v in results.items()}, "trained": trained, "samples": samples, "results": results}
