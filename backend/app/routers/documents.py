from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models as M, services as S
from app.auth import require
from app.config import UPLOAD_DIR
from app.db import get_db
from ml.ingestion import ALLOWED, MAX_BYTES, chunk_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def documents(db: Session = Depends(get_db), _=Depends(require("viewer"))):
    counts = dict(db.query(M.DocumentChunk.document_pk, func.count()).group_by(M.DocumentChunk.document_pk).all())
    latest = {(v.family, v.version): v.is_latest for v in db.query(M.DocumentVersion)}
    return [{"id": d.id, "document_id": d.document_id, "title": d.title, "family": d.family, "version": d.version, "source": d.source,
             "chunks": counts.get(d.id, 0), "is_latest": latest.get((d.family, d.version), False), "created_at": d.created_at.isoformat()}
            for d in db.query(M.Document).order_by(M.Document.family, M.Document.version)]


@router.get("/{document_id}/chunks")
def chunks(document_id: str, db: Session = Depends(get_db), _=Depends(require("viewer"))):
    rows = db.query(M.DocumentChunk).filter_by(document_id=document_id).order_by(M.DocumentChunk.chunk_index).all()
    if not rows:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    return [{"chunk_id": r.chunk_id, "section": r.section, "page": r.page, "chunk_index": r.chunk_index, "content": r.content, "content_hash": r.content_hash,
             "source": r.source, "version": r.version} for r in rows]


@router.post("/upload")
async def upload(file: UploadFile = File(...), version: int | None = Form(None), db: Session = Depends(get_db), _=Depends(require("researcher"))):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"Tipe file tidak didukung. Gunakan: {', '.join(sorted(ALLOWED))}")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Ukuran file maksimal 10 MB")
    stem = re.sub(r"[^A-Za-z0-9_\-]", "_", Path(file.filename).stem)[:80] or "dokumen"
    if version and not re.search(r"_v\d+$", stem):
        stem = f"{stem}_v{version}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{stem}{ext}"
    path.write_bytes(data)
    try:
        parsed = chunk_document(path)
    except Exception as e:  # noqa: BLE001
        path.unlink(missing_ok=True)
        raise HTTPException(422, f"Gagal memproses dokumen: {e}")
    if not parsed["chunks"]:
        raise HTTPException(422, "Tidak ada teks yang dapat diekstrak")
    doc = S.ingest_chunks(db, parsed)
    return {"document_id": doc.document_id, "version": doc.version, "chunks": len(parsed["chunks"]), "request_id": uuid.uuid4().hex[:8]}
