"""Registry tool MCP. Satu implementasi dipakai UI (MCP Tools page) dan server MCP (mcp-server/server.py)."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.db import get_db
from app.routers import dashboard, evaluation, failures, rag, registry, training

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

TOOLS = {
    "evaluate_rag": ("Jalankan query + evaluasi + deteksi kegagalan", {"query": "str", "model_version": "str?"}),
    "inspect_retrieval": ("Lihat ranking retrieval untuk sebuah query", {"query": "str"}),
    "get_failure_cases": ("Daftar failure case dengan filter", {"filters": "object?"}),
    "get_failure_case": ("Detail satu failure case", {"failure_id": "int"}),
    "generate_training_set": ("Bangun dataset training dari hard negative approved", {}),
    "generate_hard_negatives": ("Mining hard negative untuk failure terkait query", {"query": "str"}),
    "run_ab_test": ("Bandingkan dua model pada dataset sama", {"model_a": "str", "model_b": "str", "dataset": "str?"}),
    "compare_models": ("Bandingkan metrik tersimpan dua model", {"model_a": "str", "model_b": "str"}),
    "get_model_metrics": ("Metrik satu versi model", {"model_version": "str"}),
    "get_rag_metrics": ("Ringkasan KPI dashboard", {}),
    "trigger_retraining": ("Mulai training dari dataset", {"dataset_id": "int"}),
    "get_training_status": ("Status job training", {"job_id": "int"}),
}


def dispatch(db: Session, tool: str, a: dict):
    if tool == "evaluate_rag":
        return rag.execute_query(db, rag.QueryIn(query=a["query"], model_version=a.get("model_version")), require_gt=True)
    if tool == "inspect_retrieval":
        out = rag.execute_query(db, rag.QueryIn(query=a["query"], persist=False))
        return {"query_class": out["query_class"], "results": [{"rank": i + 1, "chunk_id": c["chunk_id"], "similarity": round(c["similarity"], 4), "reranking_score": round(c["reranking_score"], 4)}
                                                               for i, c in enumerate(out["reranked"])], "diagnosis": out.get("diagnosis")}
    if tool == "get_failure_cases":
        return failures.list_failures(db, **{k: v for k, v in (a.get("filters") or {}).items() if k in failures.list_failures.__code__.co_varnames})
    if tool == "get_failure_case":
        return failures.failure_detail(db, int(a["failure_id"]))
    if tool == "generate_training_set":
        d = S.build_dataset(db, "mcp-generated")
        return {"dataset_id": d.id, "stats": d.stats}
    if tool == "generate_hard_negatives":
        f = db.query(M.FailureCase).filter(M.FailureCase.query_text.ilike(a["query"])).order_by(M.FailureCase.id.desc()).first()
        if not f:
            raise HTTPException(404, "Tidak ada failure case untuk query tersebut")
        return {"failure_id": f.id, "generated": failures.generate_for_failure(db, f.id)}
    if tool == "run_ab_test":
        return evaluation.compute_ab(db, a["model_a"], a["model_b"], a.get("dataset", "eval_default"))
    if tool == "compare_models":
        va, vb = (db.query(M.ModelVersion).filter_by(version=a[k]).first() for k in ("model_a", "model_b"))
        if not va or not vb:
            raise HTTPException(404, "Model tidak ditemukan")
        return {"a": va.metrics, "b": vb.metrics, "delta": {k: round((vb.metrics or {}).get(k, 0) - (va.metrics or {}).get(k, 0), 4) for k in (va.metrics or {})}}
    if tool == "get_model_metrics":
        v = db.query(M.ModelVersion).filter_by(version=a["model_version"]).first()
        if not v:
            raise HTTPException(404, "Model tidak ditemukan")
        return {"version": v.version, "status": v.status, "metrics": v.metrics}
    if tool == "get_rag_metrics":
        return dashboard.dashboard_metrics(db)["kpis"]
    if tool == "trigger_retraining":
        job = training.start_job(db, training.StartIn(dataset_id=int(a["dataset_id"])).model_dump())
        return {"job_id": job.id, "status": job.status}
    if tool == "get_training_status":
        return training.job_status(db, int(a["job_id"]))
    raise HTTPException(404, f"Tool {tool} tidak dikenal")


@router.get("/tools")
def tools(_=Depends(require("viewer"))):
    return [{"name": n, "description": d, "params": p} for n, (d, p) in TOOLS.items()]


class InvokeIn(BaseModel):
    tool: str
    arguments: dict = {}


@router.post("/invoke")
def invoke(body: InvokeIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    try:
        return dispatch(db, body.tool, body.arguments)
    except KeyError as e:
        raise HTTPException(422, f"Argumen wajib hilang: {e}")
