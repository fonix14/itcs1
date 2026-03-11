from __future__ import annotations
from fastapi import Header, HTTPException, status
from uuid import UUID

def get_actor(x_user_id: str | None = Header(default=None, alias="X-User-Id"),
              x_user_role: str | None = Header(default=None, alias="X-User-Role")):
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Actor context required (X-User-Id, X-User-Role)")
    try:
        UUID(x_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id UUID")
    role = x_user_role.strip().lower()
    if role not in ("dispatcher","manager"):
        raise HTTPException(status_code=400, detail="Invalid X-User-Role")
    return x_user_id, role
