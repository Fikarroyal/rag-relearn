from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'rag_relearn.db'}")
QDRANT_URL = os.getenv("QDRANT_URL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "hashing-512-local")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "linear-reranker")
LLM_MODEL = os.getenv("LLM_MODEL", "mock-extractive")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8765")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "ganti-secret-ini-di-env-minimal-32-karakter")
UPLOAD_DIR = ROOT / "data" / "uploads"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
