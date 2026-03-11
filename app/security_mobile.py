from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException


@dataclass
class MobileActor:
    user_id: str
    role: str


async def get_mobile_actor(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
) -> MobileActor:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    if not x_user_role:
        raise HTTPException(status_code=401, detail="X-User-Role header is required")

    role = x_user_role.strip().lower()
    if role not in {"manager", "dispatcher"}:
        raise HTTPException(status_code=403, detail="Unsupported role")

    try:
        UUID(str(x_user_id))
    except Exception:
        raise HTTPException(status_code=400, detail="X-User-Id must be UUID")

    return MobileActor(user_id=str(x_user_id), role=role)
