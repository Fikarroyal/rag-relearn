from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import models as M
from app.config import CORS_ORIGINS
from app.db import Base, SessionLocal, engine
from app.routers import dashboard, documents, evaluation, failures, mcp, rag, registry, system, training

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("rag-relearn")

app = FastAPI(title="RAG-Relearn API", version="1.0.0", description="Retrieval Failure Analysis and Continuous RAG Improvement")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(engine)


@app.middleware("http")
async def observe(request: Request, call_next):
    rid, t0 = uuid.uuid4().hex[:12], time.perf_counter()
    status = 500
    try:
        resp = await call_next(request)
        status = resp.status_code
        resp.headers["X-Request-ID"] = rid
        return resp
    finally:
        ms = (time.perf_counter() - t0) * 1000
        log.info(json.dumps({"event": "request", "request_id": rid, "method": request.method, "path": request.url.path, "status": status, "latency_ms": round(ms, 2)}))
        if request.url.path.startswith("/api") and request.url.path != "/api/health":
            db = SessionLocal()
            try:
                db.add(M.RequestLog(request_id=rid, method=request.method, path=request.url.path[:200], status=status, latency_ms=ms))
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
            finally:
                db.close()


for r in (rag, failures, training, registry, evaluation, documents, dashboard, system, mcp):
    app.include_router(r.router)
