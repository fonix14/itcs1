from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from app.auth import get_actor_from_session_or_header


@dataclass
class MobileActor:
    user_id: str
    role: str


async def get_mobile_actor(
    request: Request,
    actor: tuple[str | None, str | None] = Depends(get_actor_from_session_or_header),
) -> MobileActor:
    x_user_id, x_user_role = actor

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Login required")
    if not x_user_role:
        raise HTTPException(status_code=401, detail="Role required")

    role = str(x_user_role).strip().lower()
    if role not in {"manager", "dispatcher", "admin"}:
        raise HTTPException(status_code=403, detail="Unsupported role")

    try:
        UUID(str(x_user_id))
    except Exception:
        raise HTTPException(status_code=400, detail="X-User-Id must be UUID")

    return MobileActor(user_id=str(x_user_id), role=role)
