from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.db import get_db
from ml.pipeline import run_rag
from ml.evaluation.metrics import evaluate_record
from ml.failure_detection.detector import detect
from ml.experiments.closed_loop import load_eval, load_train_queries

router = APIRouter(prefix="/api", tags=["rag"])


class QueryIn(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)
    threshold: float = Field(0.0, ge=0, le=1)
    reranker: str | None = None  # "none" untuk menonaktifkan
    llm: str | None = None
    embedding_model: str | None = None
    model_version: str | None = None
    ground_truth_chunk: str | None = None
    persist: bool = True


def find_ground_truth(query: str):
    for item in load_eval() + load_train_queries():
        if item["query"].strip().lower() == query.strip().lower():
            return item["ground_truth_chunk"], item.get("ground_truth")
    return None, None


def execute_query(db: Session, body: QueryIn, require_gt: bool = False) -> dict:
    store = S.get_store(db)
    if not store.chunks:
        raise HTTPException(409, "Belum ada dokumen. Jalankan seed atau upload dokumen.")
    version = body.model_version or S.production_version(db)
    rt = S.model_runtime(db, version)
    gt, gt_text = body.ground_truth_chunk, None
    if not gt:
        gt, gt_text = find_ground_truth(body.query)
    if require_gt and not gt:
        raise HTTPException(422, "Ground truth tidak ditemukan untuk query ini; sertakan ground_truth_chunk.")
    rec = run_rag(body.query, store, weights=rt["weights"], top_k=body.top_k, threshold=body.threshold,
                  use_reranker=rt["use_reranker"] and body.reranker != "none", version_guard=rt["version_guard"],
                  llm=body.llm, ground_truth_chunk=gt, model_version=version)
    rec["ground_truth"] = gt_text
    if gt:
        rec["eval"] = evaluate_record(rec)
        rec["diagnosis"] = detect(rec)
    ids = S.persist_record(db, rec, runtime=rt) if body.persist else {}
    return {**S.public_record(rec), **ids}


@router.post("/rag/query")
def rag_query(body: QueryIn, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return execute_query(db, body)


@router.post("/rag/evaluate")
def rag_evaluate(body: QueryIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    return execute_query(db, body, require_gt=True)


@router.get("/rag/history")
def history(limit: int = 50, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    rows = db.query(M.RagEvaluation).order_by(M.RagEvaluation.timestamp.desc()).limit(min(limit, 200)).all()
    return [{"evaluation_id": r.id, "query_id": r.query_id, "query": r.query.text, "query_class": r.query.query_class, "failure_type": r.failure_type,
             "model_version": r.model_version, "confidence_score": r.confidence_score, "latency_ms": (r.latency or {}).get("total_ms"),
             "timestamp": r.timestamp.isoformat(), "answer": r.answer} for r in rows]


@router.get("/retrieval/{query_id}")
def retrieval(query_id: int, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    q = db.get(M.Query, query_id)
    if not q:
        raise HTTPException(404, "Query tidak ditemukan")
    ev = db.query(M.RagEvaluation).filter_by(query_id=query_id).first()
    rows = db.query(M.RetrievalResult).filter_by(query_id=query_id).order_by(M.RetrievalResult.rank).all()
    cm = S.chunk_map(db, [r.chunk_id for r in rows] + ([ev.ground_truth_chunk] if ev and ev.ground_truth_chunk else []))
    return {"query": q.text, "query_class": q.query_class, "model_version": q.model_version, "answer": ev.answer if ev else None,
            "expected": cm.get(ev.ground_truth_chunk) if ev else None, "failure_type": ev.failure_type if ev else None,
            "failure_reason": ev.failure_reason if ev else None, "latency": ev.latency if ev else None,
            "results": [{"rank": r.rank, "original_rank": r.original_rank, "similarity": r.similarity, "reranking_score": r.reranking_score,
                         "selected": r.selected, "correct": bool(ev and r.chunk_id == ev.ground_truth_chunk), **cm.get(r.chunk_id, {"chunk_id": r.chunk_id})} for r in rows]}


class Feedback(BaseModel):
    feedback: str


@router.post("/rag/{evaluation_id}/feedback")
def feedback(evaluation_id: int, body: Feedback, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    ev = db.get(M.RagEvaluation, evaluation_id)
    if not ev:
        raise HTTPException(404, "Evaluasi tidak ditemukan")
    ev.user_feedback = body.feedback[:40]
    db.commit()
    return {"ok": True}
