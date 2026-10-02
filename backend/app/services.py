"""Business logic: store vektor, persist hasil query/evaluasi/failure, pembangunan dataset, auth."""

from __future__ import annotations
import hashlib
import hmac
import os
import sys
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models as M
from app.config import EMBEDDING_MODEL, ROOT

sys.path.insert(0, str(ROOT))
from ml.retrieval.retriever import VectorStore  # noqa: E402

_cache: dict = {"store": None}


def invalidate_store():
    _cache["store"] = None


def get_store(db: Session) -> VectorStore:
    if _cache["store"] is None:
        rows = db.query(M.DocumentChunk).all()
        _cache["store"] = VectorStore([{
            "chunk_id": r.chunk_id, "document_id": r.document_id, "family": r.family, "title": r.title, "version": r.version,
            "section": r.section, "page": r.page, "source": r.source, "content": r.content, "content_hash": r.content_hash,
            "vector": r.vector} for r in rows])
    return _cache["store"]


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    return salt.hex() + ":" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 120_000).hex()


def check_password(pw: str, stored: str) -> bool:
    salt, _ = stored.split(":")
    return hmac.compare_digest(hash_password(pw, bytes.fromhex(salt)), stored)


def ingest_chunks(db: Session, parsed: dict) -> M.Document:
    """Simpan dokumen hasil ml.ingestion.chunk_document; versi terbaru per family ditandai ulang."""
    old = db.query(M.Document).filter_by(document_id=parsed["document_id"]).first()
    if old:
        db.delete(old)
        db.flush()
    doc = M.Document(document_id=parsed["document_id"], family=parsed["family"], title=parsed["title"], version=parsed["version"], source=parsed["source"])
    db.add(doc)
    db.flush()
    for c in parsed["chunks"]:
        db.add(M.DocumentChunk(document_pk=doc.id, **{k: c[k] for k in (
            "chunk_id", "document_id", "family", "title", "version", "section", "page", "chunk_index", "source", "content", "content_hash")}, vector=c["vector"]))
    db.add(M.DocumentVersion(document_pk=doc.id, family=doc.family, version=doc.version, content_hash=parsed["chunks"][0]["content_hash"] if parsed["chunks"] else ""))
    db.flush()
    latest = max((d.version for d in db.query(M.Document).filter_by(family=doc.family)), default=0)
    for v in db.query(M.DocumentVersion).filter_by(family=doc.family):
        v.is_latest = v.version == latest
    db.commit()
    invalidate_store()
    return doc


def model_runtime(db: Session, version: str) -> dict:
    mv = db.query(M.ModelVersion).filter_by(version=version).first()
    cfg = (mv.config if mv else None) or {"use_reranker": True}
    return {"weights": mv.weights if mv else None, "use_reranker": cfg.get("use_reranker", True), "version_guard": cfg.get("version_guard", False),
            "reranker": mv.reranker if mv else "none", "mv": mv}


def production_version(db: Session) -> str:
    mv = db.query(M.ModelVersion).filter_by(status="production").first()
    return mv.version if mv else "v1"


def persist_record(db: Session, rec: dict, ts: datetime | None = None, runtime: dict | None = None) -> dict:
    """Simpan Query + RetrievalResult + RagEvaluation (+ FailureCase bila ada diagnosis)."""
    ts = ts or datetime.utcnow()
    q = M.Query(request_id=rec["request_id"], text=rec["query"], query_class=rec["query_class"]["type"], model_version=rec["model_version"], created_at=ts)
    db.add(q)
    db.flush()
    orig = {c["chunk_id"]: i + 1 for i, c in enumerate(rec["retrieved"])}
    sel = {c["chunk_id"] for c in rec["selected"]}
    for i, c in enumerate(rec["reranked"]):
        db.add(M.RetrievalResult(query_id=q.id, chunk_id=c["chunk_id"], rank=i + 1, similarity=c["similarity"], reranking_score=c["reranking_score"],
                                 original_rank=orig.get(c["chunk_id"]), selected=c["chunk_id"] in sel))
    diag = rec.get("diagnosis")
    ev = rec.get("eval") or {}
    reranker = (runtime or {}).get("reranker", "linear-reranker")
    tokens = len(rec["answer"].split()) + sum(len(c["content"].split()) for c in rec["selected"])
    e = M.RagEvaluation(query_id=q.id, answer=rec["answer"], citations=rec["citations"], ground_truth=rec.get("ground_truth"),
                        ground_truth_chunk=rec.get("ground_truth_chunk"), failure_type=diag["failure_type"] if diag else None,
                        failure_reason=diag["root_cause"] if diag else None, latency=rec["metrics"], metrics={**ev, "tokens": tokens},
                        model_version=rec["model_version"], embedding_model=EMBEDDING_MODEL, reranker_version=reranker,
                        confidence_score=rec["confidence_score"], timestamp=ts)
    db.add(e)
    db.flush()
    fc = None
    if diag:
        fc = M.FailureCase(evaluation_id=e.id, query_text=rec["query"], failure_type=diag["failure_type"], severity=diag["severity"],
                           model_version=rec["model_version"], retriever="vector-cosine", reranker=reranker,
                           similarity=rec["reranked"][0]["similarity"] if rec["reranked"] else 0, ground_truth=rec.get("ground_truth_chunk"),
                           diagnosis=diag, created_at=ts)
        db.add(fc)
        db.flush()
    db.commit()
    return {"query_id": q.id, "evaluation_id": e.id, "failure_id": fc.id if fc else None}


def public_record(rec: dict) -> dict:
    strip = lambda cs: [{k: v for k, v in c.items() if k != "vector"} for c in cs]
    return {**{k: v for k, v in rec.items() if k not in ("retrieved", "reranked", "selected")},
            "retrieved": strip(rec["retrieved"]), "reranked": strip(rec["reranked"]), "selected": strip(rec["selected"])}


def chunk_map(db: Session, ids) -> dict:
    rows = db.query(M.DocumentChunk).filter(M.DocumentChunk.chunk_id.in_(list(ids))).all()
    return {r.chunk_id: {"chunk_id": r.chunk_id, "document_id": r.document_id, "title": r.title, "version": r.version, "section": r.section,
                         "page": r.page, "source": r.source, "content": r.content} for r in rows}


def dataset_stats(samples: list[dict], validation: dict) -> dict:
    from collections import Counter
    split = Counter(s["split"] for s in samples)
    keys = {(s["query"], s["positive"], s["hard_negative"]) for s in samples}
    return {"n_samples": len(samples), "split": dict(split), "failure_distribution": dict(Counter(s["failure_type"] for s in samples)),
            "duplicates": len(samples) - len(keys), "quality_score": round(sum(s.get("quality_score", 0) for s in samples) / max(len(samples), 1), 3),
            "valid": validation["ok"], "n_issues": len(validation["issues"])}


def build_dataset(db: Session, name: str, statuses=("approved",)) -> M.TrainingDataset:
    from ml.hard_negative import dataset as ds
    rows = db.query(M.HardNegative).filter(M.HardNegative.status.in_(statuses)).all()
    seen, samples = set(), []
    for r in rows:
        key = (r.query, r.positive, r.hard_negative)
        if key in seen:
            continue
        seen.add(key)
        samples.append({"query": r.query, "positive": r.positive, "hard_negative": r.hard_negative, "reason": r.reason,
                        "failure_type": r.failure_type or "false_positive_retrieval", "quality_score": r.quality_score or 0})
    valid_ids = {c[0] for c in db.query(M.DocumentChunk.chunk_id).all()}
    samples = ds.split(samples)
    validation = ds.validate(samples, valid_ids)
    validation["train_test_leakage"] = ds.leakage(samples)
    dset = M.TrainingDataset(name=name, stats=dataset_stats(samples, validation), validation=validation)
    db.add(dset)
    db.flush()
    for s in samples:
        db.add(M.TrainingSample(dataset_id=dset.id, **{k: s[k] for k in ("query", "positive", "hard_negative", "reason", "failure_type", "split", "quality_score")}))
    db.commit()
    return dset


def next_version(db: Session) -> str:
    nums = [int(v.version[1:]) for v in db.query(M.ModelVersion) if v.version[1:].isdigit()]
    return f"v{max(nums, default=0) + 1}"
