from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.db import get_db
from ml.evaluation.runner import run_batch
from ml.experiments.closed_loop import load_eval, run_experiment

router = APIRouter(prefix="/api", tags=["evaluation"])
LOWER_IS_BETTER = {"latency_ms", "hallucination_rate", "failure_rate"}


def run_eval(db: Session, version: str, top_k=5, use_reranker=None):
    rt = S.model_runtime(db, version)
    ur = rt["use_reranker"] if use_reranker is None else use_reranker
    out = run_batch(load_eval(), S.get_store(db), weights=rt["weights"], top_k=top_k, use_reranker=ur, version_guard=rt["version_guard"], model_version=version)
    return out, rt, ur


def compute_ab(db: Session, a: str, b: str, dataset: str = "eval_default") -> dict:
    ra, _, _ = run_eval(db, a)
    rb, _, _ = run_eval(db, b)
    keys = list(ra["metrics"])
    rows = []
    for k in keys:
        va, vb = ra["metrics"][k], rb["metrics"][k]
        rows.append({"metric": k, "a": va, "b": vb, "delta": round(vb - va, 4), "lower_is_better": k in LOWER_IS_BETTER,
                     "improved": (vb < va) if k in LOWER_IS_BETTER else (vb > va)})
    return {"model_a": a, "model_b": b, "dataset": dataset, "n_queries": len(load_eval()), "rows": rows, "note": "Hasil pengukuran mentah; keputusan promosi model ada pada reviewer."}


class EvalIn(BaseModel):
    model_version: str
    dataset: str = "eval_default"
    top_k: int = 5
    retriever: str = "vector-cosine"
    reranker: str | None = None


@router.post("/evaluation/run")
def evaluation_run(body: EvalIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    if not db.query(M.ModelVersion).filter_by(version=body.model_version).first():
        raise HTTPException(404, "Model version tidak ditemukan")
    out, rt, ur = run_eval(db, body.model_version, body.top_k, None if body.reranker is None else body.reranker != "none")
    per = [{"query": r["query"], "top1": r["reranked"][0]["chunk_id"], "ground_truth": r["ground_truth_chunk"], "failure_type": r["diagnosis"]["failure_type"] if r["diagnosis"] else None,
            **r["eval"]} for r in out["records"]]
    run = M.EvaluationRun(dataset=body.dataset, model_version=body.model_version, retriever=body.retriever, reranker=rt["reranker"] if ur else "none", top_k=body.top_k, metrics=out["metrics"], per_query=per)
    db.add(run)
    db.commit()
    return {"id": run.id, "metrics": run.metrics, "per_query": per}


@router.get("/evaluation")
def evaluations(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [{"id": r.id, "dataset": r.dataset, "model_version": r.model_version, "reranker": r.reranker, "top_k": r.top_k, "metrics": r.metrics, "created_at": r.created_at.isoformat()}
            for r in db.query(M.EvaluationRun).order_by(M.EvaluationRun.id.desc()).limit(50)]


@router.get("/evaluation/{rid}")
def evaluation(rid: int, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    r = db.get(M.EvaluationRun, rid)
    if not r:
        raise HTTPException(404, "Evaluation run tidak ditemukan")
    return {"id": r.id, "dataset": r.dataset, "model_version": r.model_version, "reranker": r.reranker, "top_k": r.top_k, "metrics": r.metrics, "per_query": r.per_query,
            "created_at": r.created_at.isoformat()}


class AbIn(BaseModel):
    model_a: str
    model_b: str
    dataset: str = "eval_default"


@router.post("/ab-test")
def ab_test(body: AbIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    for v in (body.model_a, body.model_b):
        if not db.query(M.ModelVersion).filter_by(version=v).first():
            raise HTTPException(404, f"Model {v} tidak ditemukan")
    t = M.AbTest(model_a=body.model_a, model_b=body.model_b, dataset=body.dataset, results=compute_ab(db, body.model_a, body.model_b, body.dataset))
    db.add(t)
    db.commit()
    return {"id": t.id, **t.results}


@router.get("/ab-test")
def ab_tests(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [{"id": t.id, "model_a": t.model_a, "model_b": t.model_b, "dataset": t.dataset, "created_at": t.created_at.isoformat()} for t in db.query(M.AbTest).order_by(M.AbTest.id.desc())]


@router.get("/ab-test/{tid}")
def ab_get(tid: int, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    t = db.get(M.AbTest, tid)
    if not t:
        raise HTTPException(404, "A/B test tidak ditemukan")
    return {"id": t.id, **t.results}


@router.get("/experiments")
def experiments(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [{"id": e.id, "exp_id": e.exp_id, "baseline": e.baseline, "candidate": e.candidate, "dataset": e.dataset, "config": e.config, "metrics": e.metrics,
             "improvement": e.improvement, "status": e.status, "created_at": e.created_at.isoformat()} for e in db.query(M.Experiment).order_by(M.Experiment.id.desc())]


@router.post("/experiments/run")
def experiments_run(epochs: int = 40, lr: float = 0.5, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    exp = run_experiment(S.get_store(db), epochs=epochs, lr=lr)
    base, cand = exp["summary"]["baseline"], exp["summary"]["rag_relearn"]
    n = db.query(M.Experiment).count() + 1  # eksperimen lama tidak pernah dihapus
    e = M.Experiment(exp_id=f"EXP-{n:03d}", baseline="baseline", candidate="rag_relearn", dataset="eval_default",
                     config={"epochs": epochs, "learning_rate": lr, "n_samples": len(exp["samples"]), "seed": 42}, metrics=exp["summary"],
                     improvement={k: round(cand[k] - base[k], 4) for k in base})
    db.add(e)
    db.commit()
    return {"exp_id": e.exp_id, "metrics": e.metrics, "improvement": e.improvement}
