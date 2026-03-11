from __future__ import annotations

from typing import Any
from sqlalchemy import text


async def _one(session, sql: str, params: dict[str, Any] | None = None):
    try:
        res = await session.execute(text(sql), params or {})
        row = res.mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


async def resolve_actor_profile(session, actor_user_id: str, actor_role: str):
    user = await _one(
        session,
        """
        select id::text as id,
               coalesce(full_name, email, id::text) as display_name,
               role
        from users
        where id = cast(:user_id as uuid)
        """,
        {"user_id": actor_user_id},
    )

    if not user:
        return {
            "user_id": actor_user_id,
            "display_name": actor_user_id,
            "role": actor_role,
            "exists_in_users": False,
        }

    return {
        "user_id": user["id"],
        "display_name": user["display_name"],
        "role": actor_role,
        "exists_in_users": True,
    }
