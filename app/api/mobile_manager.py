from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_actor_from_session_or_header
from app.db import db_session

router = APIRouter(prefix="/api/mobile", tags=["mobile-manager"])


async def _resolve_actor(
    request: Request,
    actor: tuple[str | None, str | None] = Depends(get_actor_from_session_or_header),
) -> tuple[str | None, str | None]:
    actor_user_id, actor_role = actor
    role = (actor_role or "manager").strip().lower()
    return actor_user_id, role


@router.get("/tasks")
async def mobile_tasks(
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor

    if not actor_user_id:
        raise HTTPException(status_code=401, detail="Login required")

    try:
        if actor_role in {"dispatcher", "admin"}:
            result = await session.execute(
                text(
                    """
                    select
                        t.id::text as id,
                        t.portal_task_id,
                        t.status,
                        t.sla_due_at as sla,
                        t.last_seen_at,
                        coalesce(t.internal_status, 'new') as internal_status,
                        s.store_no,
                        s.name as store_name
                    from tasks t
                    join stores s on s.id = t.store_id
                    order by
                        case when t.sla_due_at is null then 1 else 0 end,
                        t.sla_due_at asc nulls last,
                        t.last_seen_at desc nulls last
                    """
                )
            )
        else:
            result = await session.execute(
                text(
                    """
                    select
                        t.id::text as id,
                        t.portal_task_id,
                        t.status,
                        t.sla_due_at as sla,
                        t.last_seen_at,
                        coalesce(t.internal_status, 'new') as internal_status,
                        s.store_no,
                        s.name as store_name
                    from tasks t
                    join stores s on s.id = t.store_id
                    where s.assigned_user_id = cast(:user_id as uuid)
                    order by
                        case when t.sla_due_at is null then 1 else 0 end,
                        t.sla_due_at asc nulls last,
                        t.last_seen_at desc nulls last
                    """
                ),
                {"user_id": actor_user_id},
            )

        rows = [dict(r) for r in result.mappings().all()]
        return {"status": "ok", "data": rows}

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}
