from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_dispatcher
from app.db import db_session

router = APIRouter(
    tags=["tasks_ui"],
    dependencies=[Depends(require_dispatcher)],
)


@router.get("/api/tasks")
async def api_tasks(
    overdue_only: bool = Query(default=False),
    session: AsyncSession = Depends(db_session),
):
    try:
        where_sql = ""
        if overdue_only:
            where_sql = """
            where t.sla_due_at is not null
              and t.sla_due_at < now()
            """

        result = await session.execute(
            text(
                f"""
                select
                    t.id::text as id,
                    t.portal_task_id,
                    t.status as status,
                    coalesce(t.internal_status, 'new') as internal_status,
                    t.sla_due_at as sla,
                    t.last_seen_at,
                    s.store_no,
                    coalesce(u.full_name, u.email, '—') as manager_name
                from tasks t
                left join stores s on s.id = t.store_id
                left join users u on u.id = s.assigned_user_id
                {where_sql}
                order by
                    case when t.sla_due_at is null then 1 else 0 end,
                    t.sla_due_at asc,
                    t.created_at desc
                limit 100
                """
            )
        )

        rows = [dict(r) for r in result.mappings().all()]
        return {"status": "ok", "data": rows}

    except Exception as e:
        return {"status": "error", "error": str(e)}
