"""JWT + role-based access (Admin > Researcher > Viewer). AUTH_ENABLED=false untuk demo lokal."""

from __future__ import annotations
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AUTH_ENABLED, JWT_SECRET

bearer = HTTPBearer(auto_error=False)
RANK = {"viewer": 1, "researcher": 2, "admin": 3}


def make_token(username: str, role: str) -> str:
    return jwt.encode({"sub": username, "role": role, "exp": datetime.utcnow() + timedelta(hours=12)}, JWT_SECRET, algorithm="HS256")


def require(role: str = "viewer"):
    def dep(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if not AUTH_ENABLED:
            return {"sub": "demo", "role": "admin"}
        if not cred:
            raise HTTPException(401, "Token diperlukan")
        try:
            data = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise HTTPException(401, "Token tidak valid atau kedaluwarsa")
        if RANK.get(data.get("role"), 0) < RANK[role]:
            raise HTTPException(403, f"Butuh role {role}")
        return data
    return dep
