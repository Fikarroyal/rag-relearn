from __future__ import annotations

from pathlib import Path

import pytest

from ml.common import embed, content_hash
from ml.ingestion import chunk_document, parse_name, sanitize, extract_text
from ml.retrieval.classifier import classify
from ml.retrieval.retriever import latest_versions
from ml.reranking.reranker import LinearReranker
from ml.pipeline import run_rag
from ml.failure_detection.detector import detect
from ml.hard_negative.miner import mine
from ml.hard_negative import dataset as ds
from ml.evaluation import metrics as mt
from ml.evaluation.runner import run_batch
from ml.experiments.closed_loop import load_eval, run_experiment
from ml.training.trainer import train

SEED = Path(__file__).resolve().parents[1] / "data" / "seed_docs"
QUERY = "Bagaimana prosedur backup server?"
GT = "SOP_Backup_v4_section_3"


def test_ingestion_chunks_have_required_metadata():
    parsed = chunk_document(SEED / "SOP_Backup_v4.md")
    assert parsed["version"] == 4 and len(parsed["chunks"]) == 6
    for k in ("document_id", "version", "section", "page", "chunk_index", "source", "content_hash"):
        assert all(c[k] not in (None, "") for c in parsed["chunks"]), k


def test_sanitize_and_validation(tmp_path):
    assert "<script" not in sanitize("a <script>alert(1)</script> b")
    bad = tmp_path / "x.exe"
    bad.write_text("x")
    with pytest.raises(ValueError):
        extract_text(bad)
    assert parse_name("SOP_Backup_v4") == ("SOP_Backup", 4)


def test_embedding_deterministic_and_normalized():
    a, b = embed("backup server"), embed("backup server")
    assert (a == b).all() and abs(float((a @ a)) - 1) < 1e-5
    assert content_hash("a  b") == content_hash("a b")


def test_classifier_strategy():
    assert classify("versi terbaru SOP backup")["type"] == "version_sensitive"
    assert classify("Bagaimana prosedur backup server?")["strategy"]["prefer_latest"]
    assert classify("backup")["type"] == "ambiguous"


def test_retrieval_finds_all_backup_versions(store):
    res = store.search(QUERY, top_k=10)
    versions = {c["version"] for c in res if c["family"] == "SOP_Backup"}
    assert {2, 3, 4} <= versions


def test_baseline_picks_wrong_version_and_detector_flags_it(store):
    rec = run_rag(QUERY, store, use_reranker=False, ground_truth_chunk=GT)
    assert rec["reranked"][0]["chunk_id"] != GT
    d = detect(rec)
    assert d["failure_type"] == "document_version_mismatch"
    assert d["evidence"] and d["recommended_action"] and d["root_cause"]


def test_reranker_uses_version_feature(store):
    cands = store.search(QUERY, top_k=20)
    out = LinearReranker({"is_latest": 5.0}).rerank(QUERY, cands, latest_versions(store.chunks))
    assert out[0]["chunk_id"] == GT


def test_hard_negative_mining_prefers_wrong_version(store):
    hn = mine(QUERY, GT, store)
    assert hn and hn[0]["negative_type"] == "wrong_version"
    assert all(h["hard_negative"] != GT for h in hn)


def test_dataset_validation_and_no_leakage():
    s = [{"query": "q1", "positive": "a", "hard_negative": "b", "reason": "r", "failure_type": "f"},
         {"query": "q1", "positive": "a", "hard_negative": "b", "reason": "r", "failure_type": "f"},
         {"query": "q2", "positive": "a", "hard_negative": "a", "reason": "r", "failure_type": "f"},
         {"query": "q3", "positive": "a", "hard_negative": "zz", "reason": "", "failure_type": "f"}]
    kinds = {i["issue"] for i in ds.validate(s, {"a", "b"})["issues"]}
    assert {"duplicate_sample", "contradictory_label", "invalid_document", "missing_field"} <= kinds
    assert ds.leakage(ds.split([{**x, "query": f"q{i % 5}"} for i, x in enumerate(s * 5)])) == 0


def test_metrics_math():
    ids = ["x", "gt", "y"]
    assert mt.mrr(ids, "gt") == 0.5 and mt.recall_at_k(ids, "gt", 1) == 0 and mt.recall_at_k(ids, "gt", 3) == 1
    assert 0 < mt.ndcg(ids, "gt") < 1


def test_training_reduces_loss(store):
    samples = [{**h, "split": "train"} for q in ("Apa saja langkah backup server produksi?", QUERY) for h in mine(q, GT, store)]
    out = train(samples, [], store, epochs=15, lr=0.5)
    assert out["history"][-1]["loss"] < out["history"][0]["loss"]
    assert out["weights"]["is_latest"] > 0


def test_closed_loop_improves_over_baseline():
    """Integrasi: query -> retrieval -> evaluation -> failure detection -> dataset -> training -> evaluasi (query training terpisah dari evaluasi)."""
    exp = run_experiment(epochs=30)
    base, rel = exp["summary"]["baseline"], exp["summary"]["rag_relearn"]
    assert rel["mrr"] > base["mrr"] and rel["failure_rate"] < base["failure_rate"]
    assert exp["samples"] and ds.leakage(exp["samples"]) == 0
