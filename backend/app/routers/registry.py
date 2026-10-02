from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models as M
from app.auth import require
from app.db import get_db

router = APIRouter(prefix="/api/models", tags=["models"])
STATUSES = {"training", "candidate", "staging", "production", "archived"}


def dump(v: M.ModelVersion) -> dict:
    return {"id": v.id, "name": v.model.name, "version": v.version, "base_model": v.base_model, "embedding_model": v.embedding_model, "reranker": v.reranker,
            "training_dataset_id": v.training_dataset_id, "trained_at": v.trained_at.isoformat(), "metrics": v.metrics or {}, "status": v.status, "weights": v.weights}


@router.get("")
def models(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    return [dump(v) for v in db.query(M.ModelVersion).order_by(M.ModelVersion.id.desc())]


class RegisterIn(BaseModel):
    version: str
    base_model: str = "linear-reranker"
    embedding_model: str = "hashing-512-local"
    reranker: str = "linear-reranker"
    weights: dict | None = None
    status: str = "candidate"


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db), _=Depends(require("researcher"))):
    if db.query(M.ModelVersion).filter_by(version=body.version).first():
        raise HTTPException(409, "Versi sudah terdaftar")
    if body.status not in STATUSES:
        raise HTTPException(422, "Status tidak valid")
    mdl = db.query(M.Model).first() or M.Model(name="rag-relearn-reranker")
    db.add(mdl)
    db.flush()
    v = M.ModelVersion(model_id=mdl.id, config={"use_reranker": True}, **body.model_dump())
    db.add(v)
    db.commit()
    return dump(v)


class StatusIn(BaseModel):
    status: str


@router.post("/{vid}/status")
def set_status(vid: int, body: StatusIn, db: Session = Depends(get_db), _=Depends(require("admin"))):
    v = db.get(M.ModelVersion, vid)
    if not v:
        raise HTTPException(404, "Model tidak ditemukan")
    if body.status not in STATUSES:
        raise HTTPException(422, "Status tidak valid")
    if body.status == "production":
        for o in db.query(M.ModelVersion).filter_by(status="production"):
            o.status = "archived"
    v.status = body.status
    db.commit()
    return dump(v)
