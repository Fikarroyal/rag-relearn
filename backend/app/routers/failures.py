from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.db import get_db
from ml.hard_negative.miner import mine
from ml.failure_detection.detector import ACTION, SEVERITY

router = APIRouter(prefix="/api", tags=["failures"])
SORTABLE = {"id": M.FailureCase.id, "created_at": M.FailureCase.created_at, "similarity": M.FailureCase.similarity, "severity": M.FailureCase.severity}


def list_failures(db: Session, failure_type=None, model_version=None, retriever=None, reranker=None, severity=None, status=None, search=None,
                  date_from=None, sort="created_at", order="desc", page=1, page_size=20):
    q = db.query(M.FailureCase)
    for col, val in [(M.FailureCase.failure_type, failure_type), (M.FailureCase.model_version, model_version), (M.FailureCase.retriever, retriever),
                     (M.FailureCase.reranker, reranker), (M.FailureCase.severity, severity), (M.FailureCase.status, status)]:
        if val:
            q = q.filter(col == val)
    if search:
        q = q.filter(or_(M.FailureCase.query_text.ilike(f"%{search}%"), M.FailureCase.ground_truth.ilike(f"%{search}%")))
    if date_from:
        q = q.filter(M.FailureCase.created_at >= datetime.fromisoformat(date_from))
    total = q.count()
    col = SORTABLE.get(sort, M.FailureCase.created_at)
    q = q.order_by(col.desc() if order == "desc" else col.asc()).offset((page - 1) * page_size).limit(min(page_size, 100))
    return {"total": total, "page": page, "items": [{"id": f.id, "query": f.query_text, "failure_type": f.failure_type, "severity": f.severity,
            "model_version": f.model_version, "retriever": f.retriever, "reranker": f.reranker, "similarity": round(f.similarity or 0, 4),
            "ground_truth": f.ground_truth, "status": f.status, "created_at": f.created_at.isoformat()} for f in q]}


@router.get("/failures")
def failures(failure_type: str | None = None, model_version: str | None = None, retriever: str | None = None, reranker: str | None = None,
             severity: str | None = None, status: str | None = None, search: str | None = None, date_from: str | None = None,
             sort: str = "created_at", order: str = "desc", page: int = 1, page_size: int = 20,
             db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return list_failures(db, failure_type, model_version, retriever, reranker, severity, status, search, date_from, sort, order, page, page_size)


def failure_detail(db: Session, fid: int) -> dict:
    f = db.get(M.FailureCase, fid)
    if not f:
        raise HTTPException(404, "Failure case tidak ditemukan")
    ev = f.evaluation
    rows = db.query(M.RetrievalResult).filter_by(query_id=ev.query_id).order_by(M.RetrievalResult.rank).all()
    cm = S.chunk_map(db, [r.chunk_id for r in rows] + [f.ground_truth])
    hns = db.query(M.HardNegative).filter_by(failure_id=fid).all()
    sample = None
    if hns:
        h = hns[0]
        sample = {"query": h.query, "positive": h.positive, "hard_negative": h.hard_negative, "reason": h.reason, "failure_type": h.failure_type}
    return {"id": f.id, "query": f.query_text, "status": f.status, "severity": f.severity, "failure_type": f.failure_type, "model_version": f.model_version,
            "created_at": f.created_at.isoformat(), "answer": ev.answer, "citations": ev.citations, "ground_truth": f.ground_truth,
            "expected": cm.get(f.ground_truth), "diagnosis": f.diagnosis, "query_id": ev.query_id, "evaluation_id": ev.id,
            "retrieved": [{"rank": r.rank, "similarity": r.similarity, "reranking_score": r.reranking_score, "correct": r.chunk_id == f.ground_truth,
                           **cm.get(r.chunk_id, {"chunk_id": r.chunk_id})} for r in rows],
            "hard_negatives": [{"id": h.id, "hard_negative": h.hard_negative, "similarity": h.similarity, "negative_type": h.negative_type, "reason": h.reason,
                                "status": h.status, "confidence": h.confidence} for h in hns], "training_entry": sample}


@router.get("/failures/{fid}")
def failure(fid: int, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return failure_detail(db, fid)


def generate_for_failure(db: Session, fid: int) -> list:
    f = db.get(M.FailureCase, fid)
    if not f:
        raise HTTPException(404, "Failure case tidak ditemukan")
    existing = {h.hard_negative for h in db.query(M.HardNegative).filter_by(failure_id=fid)}
    out = []
    for hn in mine(f.query_text, f.ground_truth, S.get_store(db)):
        if hn["hard_negative"] in existing:
            continue
        row = M.HardNegative(failure_id=fid, failure_type=f.failure_type, **hn)
        db.add(row)
        out.append(hn)
    db.commit()
    return out


@router.post("/failures/{fid}/hard-negative")
def hard_negative(fid: int, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    return {"generated": generate_for_failure(db, fid)}


class StatusIn(BaseModel):
    status: str


@router.post("/failures/{fid}/status")
def set_status(fid: int, body: StatusIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    if body.status not in {"open", "investigating", "resolved"}:
        raise HTTPException(422, "Status harus open/investigating/resolved")
    f = db.get(M.FailureCase, fid)
    if not f:
        raise HTTPException(404, "Failure case tidak ditemukan")
    f.status = body.status
    db.commit()
    return {"ok": True, "status": f.status}


@router.post("/failures/{fid}/rerun")
def rerun(fid: int, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    from app.routers.rag import QueryIn, execute_query
    f = db.get(M.FailureCase, fid)
    if not f:
        raise HTTPException(404, "Failure case tidak ditemukan")
    out = execute_query(db, QueryIn(query=f.query_text, ground_truth_chunk=f.ground_truth, persist=False))
    if not out.get("diagnosis"):
        f.status = "resolved"
        db.commit()
    return {"still_failing": bool(out.get("diagnosis")), "diagnosis": out.get("diagnosis"), "top1": out["reranked"][0]["chunk_id"] if out["reranked"] else None,
            "model_version": out["model_version"]}


@router.post("/failures/{fid}/add-to-dataset")
def add_to_dataset(fid: int, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    rows = db.query(M.HardNegative).filter_by(failure_id=fid).all()
    if not rows:
        generate_for_failure(db, fid)
        rows = db.query(M.HardNegative).filter_by(failure_id=fid).all()
    for h in rows:
        if h.status != "rejected":
            h.status = "approved"
    db.commit()
    return {"approved": sum(1 for h in rows if h.status == "approved")}


class MarkIn(BaseModel):
    evaluation_id: int
    failure_type: str = "answer_relevance_failure"
    reason: str = "Ditandai manual oleh pengguna"


@router.post("/failures/mark")
def mark(body: MarkIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    ev = db.get(M.RagEvaluation, body.evaluation_id)
    if not ev:
        raise HTTPException(404, "Evaluasi tidak ditemukan")
    if body.failure_type not in ACTION:
        raise HTTPException(422, "failure_type tidak dikenal")
    diag = {"failure_type": body.failure_type, "confidence": 1.0, "evidence": ["ditandai manual"], "root_cause": body.reason,
            "recommended_action": ACTION[body.failure_type], "severity": SEVERITY.get(body.failure_type, "low")}
    ev.failure_type, ev.failure_reason = body.failure_type, body.reason
    f = M.FailureCase(evaluation_id=ev.id, query_text=ev.query.text, failure_type=body.failure_type, severity=diag["severity"], model_version=ev.model_version,
                      retriever="vector-cosine", reranker=ev.reranker_version, similarity=0, ground_truth=ev.ground_truth_chunk, diagnosis=diag)
    db.add(f)
    db.commit()
    return {"failure_id": f.id}


# ---- Hard negatives ----
@router.get("/hard-negatives")
def hard_negatives(status: str | None = None, negative_type: str | None = None, page: int = 1, page_size: int = 25,
                   db: Session = Depends(get_db), _=Depends(require("viewer"))):
    q = db.query(M.HardNegative)
    if status:
        q = q.filter_by(status=status)
    if negative_type:
        q = q.filter_by(negative_type=negative_type)
    total = q.count()
    rows = q.order_by(M.HardNegative.id.desc()).offset((page - 1) * page_size).limit(min(page_size, 100)).all()
    return {"total": total, "items": [{c.name: getattr(h, c.name) for c in M.HardNegative.__table__.columns if c.name != "created_at"} for h in rows]}


@router.post("/hard-negatives/{hid}/{action}")
def hn_action(hid: int, action: str, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    h = db.get(M.HardNegative, hid)
    if not h:
        raise HTTPException(404, "Hard negative tidak ditemukan")
    if action in ("approve", "reject"):
        h.status = "approved" if action == "approve" else "rejected"
    elif action == "regenerate":
        used = {x.hard_negative for x in db.query(M.HardNegative).filter_by(query=h.query, positive=h.positive)}
        alt = [c for c in mine(h.query, h.positive, S.get_store(db), min_similarity=0.05, max_negatives=10) if c["hard_negative"] not in used]
        if not alt:
            raise HTTPException(409, "Tidak ada kandidat alternatif")
        for k, v in alt[0].items():
            if k not in ("query", "positive"):
                setattr(h, k, v)
        h.status = "pending"
    else:
        raise HTTPException(404, "Aksi tidak dikenal")
    db.commit()
    return {"ok": True, "status": h.status, "hard_negative": h.hard_negative}
