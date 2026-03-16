from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from uuid import UUID

from app.auth import get_actor_from_session_or_header


async def get_actor(
    request: Request,
    actor: tuple[str | None, str | None] = Depends(get_actor_from_session_or_header),
):
    x_user_id, x_user_role = actor

    if not x_user_id or not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Actor context required",
        )

    try:
        UUID(str(x_user_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id UUID")

    role = str(x_user_role).strip().lower()
    if role not in ("dispatcher", "manager", "admin"):
        raise HTTPException(status_code=400, detail="Invalid X-User-Role")

    return str(x_user_id), role
