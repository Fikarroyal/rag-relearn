from __future__ import annotations

import csv
import io
import json
import threading
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.db import SessionLocal, get_db
from ml.evaluation.runner import run_batch
from ml.experiments.closed_loop import load_eval
from ml.hard_negative import dataset as ds
from ml.training.trainer import train

router = APIRouter(prefix="/api/training", tags=["training"])


class DatasetIn(BaseModel):
    name: str = Field("dataset-" + datetime.utcnow().strftime("%Y%m%d-%H%M"), max_length=120)
    include_pending: bool = False


@router.post("/dataset")
def create_dataset(body: DatasetIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    if not db.query(M.HardNegative).filter(M.HardNegative.status == "approved").count() and not body.include_pending:
        raise HTTPException(409, "Belum ada hard negative berstatus approved.")
    d = S.build_dataset(db, body.name, ("approved", "pending") if body.include_pending else ("approved",))
    return {"id": d.id, "name": d.name, "stats": d.stats, "validation": d.validation}


@router.get("/datasets")
def datasets(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [{"id": d.id, "name": d.name, "stats": d.stats, "created_at": d.created_at.isoformat()} for d in db.query(M.TrainingDataset).order_by(M.TrainingDataset.id.desc())]


@router.get("/datasets/{did}")
def dataset(did: int, split: str | None = None, page: int = 1, page_size: int = 25, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    d = db.get(M.TrainingDataset, did)
    if not d:
        raise HTTPException(404, "Dataset tidak ditemukan")
    q = db.query(M.TrainingSample).filter_by(dataset_id=did)
    if split:
        q = q.filter_by(split=split)
    rows = q.offset((page - 1) * page_size).limit(min(page_size, 200)).all()
    return {"id": d.id, "name": d.name, "stats": d.stats, "validation": d.validation, "total": q.count(),
            "samples": [{"query": s.query, "positive": s.positive, "hard_negative": s.hard_negative, "reason": s.reason, "failure_type": s.failure_type,
                         "split": s.split, "quality_score": s.quality_score} for s in rows]}


@router.get("/datasets/{did}/export")
def export(did: int, format: str = "jsonl", db: Session = Depends(get_db), _=Depends(require("viewer"))):
    rows = [{"query": s.query, "positive": s.positive, "hard_negative": s.hard_negative, "reason": s.reason, "failure_type": s.failure_type, "split": s.split}
            for s in db.query(M.TrainingSample).filter_by(dataset_id=did)]
    if not rows:
        raise HTTPException(404, "Dataset kosong atau tidak ditemukan")
    if format == "json":
        return PlainTextResponse(json.dumps(rows, ensure_ascii=False, indent=2), media_type="application/json")
    if format == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")
    return PlainTextResponse(ds.to_jsonl(rows), media_type="application/jsonl")


class StartIn(BaseModel):
    dataset_id: int
    base_model: str = "linear-reranker"
    epochs: int = Field(30, ge=1, le=200)
    learning_rate: float = Field(0.5, gt=0, le=5)
    batch_size: int = Field(8, ge=1, le=256)
    max_seq_length: int = 256
    lora_rank: int = 8
    lora_alpha: int = 16
    warmup_steps: int = 0
    mode: str = "lightweight"  # lightweight | hf


def _run_job(job_id: int):
    db = SessionLocal()
    job = db.get(M.TrainingJob, job_id)
    try:
        job.status = "running"
        db.commit()
        cfg = job.config
        samples = [{"query": s.query, "positive": s.positive, "hard_negative": s.hard_negative, "split": s.split}
                   for s in db.query(M.TrainingSample).filter_by(dataset_id=job.dataset_id)]
        tr = [s for s in samples if s["split"] == "train"] or samples
        va = [s for s in samples if s["split"] == "validation"]
        mode_used = "lightweight"
        if cfg.get("mode") == "hf":
            try:
                import torch  # noqa: F401
                import peft  # noqa: F401
                mode_used = "hf-lora (lihat ml/training/hf_lora_trainer.py); reranker linear tetap dilatih untuk integrasi pipeline"
            except ImportError:
                mode_used = "lightweight (fallback: torch/PEFT tidak terpasang)"
        hist = []

        def progress(row):
            hist.append(row)
            job.history = list(hist)
            db.commit()
            time.sleep(0.08)

        res = train(tr, va, S.get_store(db), epochs=cfg["epochs"], lr=cfg["learning_rate"], batch_size=cfg["batch_size"], progress=progress)
        ver = S.next_version(db)
        metrics = run_batch(load_eval(), S.get_store(db), weights=res["weights"], model_version=ver)["metrics"]
        mdl = db.query(M.Model).first()
        db.add(M.ModelVersion(model_id=mdl.id, version=ver, base_model=cfg["base_model"], embedding_model="hashing-512-local", reranker=f"linear-reranker-{ver}",
                              weights=res["weights"], config={"use_reranker": True, "training": cfg}, training_dataset_id=job.dataset_id, metrics=metrics, status="candidate"))
        job.result, job.model_version, job.status, job.finished_at = {**res, "mode_used": mode_used}, ver, "completed", datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        job.status, job.error, job.finished_at = "failed", str(e), datetime.utcnow()
    db.commit()
    db.close()


def start_job(db: Session, cfg: dict) -> M.TrainingJob:
    if not db.get(M.TrainingDataset, cfg["dataset_id"]):
        raise HTTPException(404, "Dataset tidak ditemukan")
    job = M.TrainingJob(dataset_id=cfg["dataset_id"], config=cfg, status="queued", history=[])
    db.add(job)
    db.commit()
    threading.Thread(target=_run_job, args=(job.id,), daemon=True).start()
    return job


@router.post("/start")
def start(body: StartIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    job = start_job(db, body.model_dump())
    return {"job_id": job.id, "status": job.status}


def job_status(db: Session, jid: int) -> dict:
    j = db.get(M.TrainingJob, jid)
    if not j:
        raise HTTPException(404, "Job tidak ditemukan")
    db.refresh(j)
    return {"id": j.id, "status": j.status, "config": j.config, "history": j.history or [], "model_version": j.model_version, "error": j.error,
            "weights": (j.result or {}).get("weights"), "mode_used": (j.result or {}).get("mode_used"), "created_at": j.created_at.isoformat(),
            "finished_at": j.finished_at.isoformat() if j.finished_at else None}


@router.get("/jobs")
def jobs(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [{"id": j.id, "status": j.status, "dataset_id": j.dataset_id, "model_version": j.model_version, "epochs_done": len(j.history or []),
             "created_at": j.created_at.isoformat()} for j in db.query(M.TrainingJob).order_by(M.TrainingJob.id.desc()).limit(30)]


@router.get("/{job_id:int}")
def job(job_id: int, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return job_status(db, job_id)
