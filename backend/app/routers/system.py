from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import make_token, require
from app.config import AUTH_ENABLED, DATABASE_URL, EMBEDDING_MODEL, LLM_MODEL, MCP_SERVER_URL, QDRANT_URL, RERANKER_MODEL
from app.db import get_db

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok", "chunks_indexed": len(S.get_store(db).chunks)}


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(M.User).filter_by(username=body.username).first()
    if not u or not S.check_password(body.password, u.password_hash):
        raise HTTPException(401, "Username atau password salah")
    return {"access_token": make_token(u.username, u.role), "token_type": "bearer", "role": u.role}


@router.get("/settings")
def settings(_=Depends(require("viewer"))):
    """Tidak pernah mengembalikan nilai API key; hanya status ketersediaan."""
    return {"auth_enabled": AUTH_ENABLED, "database": DATABASE_URL.split("://")[0], "embedding_model": EMBEDDING_MODEL, "reranker_model": RERANKER_MODEL,
            "llm_model": LLM_MODEL, "qdrant_url": QDRANT_URL or None, "mcp_server_url": MCP_SERVER_URL,
            "providers": {"openai": bool(os.getenv("OPENAI_API_KEY")), "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")), "local_mock": True},
            "upload_limit_mb": 10, "allowed_types": [".pdf", ".docx", ".txt", ".md"]}


@router.get("/observability/summary")
def observability(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    logs = db.query(M.RequestLog).order_by(M.RequestLog.id.desc()).limit(2000).all()
    evals = db.query(M.RagEvaluation).all()
    lat = sorted(l.latency_ms for l in logs) or [0]
    ms = [e.metrics or {} for e in evals]
    avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else 0
    return {"request_count": len(logs), "error_rate": avg([1 if l.status >= 500 else 0 for l in logs]), "p50_ms": lat[len(lat) // 2], "p95_ms": lat[int(len(lat) * 0.95) - 1] if len(lat) > 1 else lat[0],
            "token_usage": sum(m.get("tokens", 0) for m in ms), "retrieval_quality": avg([m.get("recall@1", 0) for m in ms]), "failure_rate": avg([1 if e.failure_type else 0 for e in evals]),
            "hallucination_rate": avg([m.get("hallucination_rate", 0) for m in ms]), "citation_accuracy": avg([m.get("citation_accuracy", 0) for m in ms]),
            "model_versions": sorted({e.model_version for e in evals})}
