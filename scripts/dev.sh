#!/usr/bin/env bash
# Mode lokal tanpa Docker: backend (SQLite) + frontend dev server.
set -e
cd "$(dirname "$0")/.."
pip install -r backend/requirements.txt

(cd backend && python -m app.seed)
(cd backend && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm install && npm run dev)
