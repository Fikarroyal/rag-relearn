from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models as M
from app.auth import require
from app.db import get_db

router = APIRouter(prefix="/api", tags=["dashboard"])
avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else 0.0


def dashboard_metrics(db: Session) -> dict:
    evals = db.query(M.RagEvaluation).order_by(M.RagEvaluation.timestamp).all()
    n = len(evals)
    ms = [e.metrics or {} for e in evals]
    lat = [e.latency or {} for e in evals]
    fails = db.query(M.FailureCase).count()
    prod = db.query(M.ModelVersion).filter_by(status="production").first()
    by_day = defaultdict(list)
    for e in evals:
        by_day[e.timestamp.strftime("%Y-%m-%d")].append(e)
    trend = [{"date": d, "success_rate": avg([(x.metrics or {}).get("recall@1", 0) for x in xs]), "failure_rate": avg([1 if x.failure_type else 0 for x in xs]),
              "retrieval_ms": avg([(x.latency or {}).get("retrieval_ms", 0) + (x.latency or {}).get("reranking_ms", 0) for x in xs]),
              "generation_ms": avg([(x.latency or {}).get("generation_ms", 0) for x in xs]), "total_ms": avg([(x.latency or {}).get("total_ms", 0) for x in xs]),
              "queries": len(xs)} for d, xs in sorted(by_day.items())]
    top = [r.similarity for r in db.query(M.RetrievalResult).filter_by(rank=1)]
    hist = [{"bucket": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "count": sum(1 for s in top if i / 10 <= s < (i + 1) / 10 or (i == 9 and s >= 1))} for i in range(10)]
    by_model = defaultdict(list)
    for e, m in zip(evals, ms):
        by_model[e.model_version].append(m)
    scores = [{"model_version": v, **{k: avg([x.get(k, 0) for x in xs]) for k in ("faithfulness", "answer_relevance", "context_precision", "citation_accuracy")}} for v, xs in sorted(by_model.items())]
    versions = db.query(M.ModelVersion).order_by(M.ModelVersion.id).all()
    job = db.query(M.TrainingJob).order_by(M.TrainingJob.id.desc()).first()
    return {
        "kpis": {"total_queries": n, "successful_retrieval": avg([m.get("recall@1", 0) for m in ms]), "retrieval_failure_rate": avg([1 if e.failure_type else 0 for e in evals]),
                 "answer_grounding": avg([m.get("faithfulness", 0) for m in ms]), "answer_relevance": avg([m.get("answer_relevance", 0) for m in ms]),
                 "avg_retrieval_ms": avg([l.get("retrieval_ms", 0) + l.get("reranking_ms", 0) for l in lat]), "avg_generation_ms": avg([l.get("generation_ms", 0) for l in lat]),
                 "total_failures": fails, "hard_negatives": db.query(M.HardNegative).count(), "current_model": prod.version if prod else None},
        "success_trend": trend, "failure_distribution": [{"type": k, "count": v} for k, v in Counter(e.failure_type for e in evals if e.failure_type).most_common()],
        "score_distribution": hist, "eval_scores": scores,
        "model_comparison": [{"version": v.version, "status": v.status, **{k: (v.metrics or {}).get(k, 0) for k in ("recall@1", "mrr", "ndcg", "context_precision", "failure_rate")}} for v in versions],
        "recent_failures": [{"id": f.id, "query": f.query_text, "failure_type": f.failure_type, "severity": f.severity, "model_version": f.model_version, "created_at": f.created_at.isoformat()}
                            for f in db.query(M.FailureCase).order_by(M.FailureCase.created_at.desc()).limit(5)],
        "recent_evaluations": [{"id": e.id, "query": e.query.text, "model_version": e.model_version, "failure_type": e.failure_type, "latency_ms": (e.latency or {}).get("total_ms"),
                                "timestamp": e.timestamp.isoformat()} for e in reversed(evals[-6:])],
        "production_model": {"version": prod.version, "reranker": prod.reranker, "embedding_model": prod.embedding_model, "metrics": prod.metrics, "trained_at": prod.trained_at.isoformat()} if prod else None,
        "training_status": {"id": job.id, "status": job.status, "epochs_done": len(job.history or []), "epochs_total": (job.config or {}).get("epochs"), "model_version": job.model_version} if job else None,
    }


@router.get("/dashboard/metrics")
def metrics(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return dashboard_metrics(db)
