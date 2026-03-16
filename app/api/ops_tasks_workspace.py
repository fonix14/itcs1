from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/ops", tags=["ops_stage175"])


class TaskWorkStatusIn(BaseModel):
    internal_status: str


@router.get("/tasks")
async def list_tasks(limit: int = 200, offset: int = 0, db: AsyncSession = Depends(get_db)):
    q = text("""
    select
        t.id::text as id,
        t.portal_task_id,
        s.store_no,
        coalesce(t.status, 'open') as portal_status,
        coalesce(t.internal_status, 'new') as internal_status,
        coalesce(t.assigned_user_id::text, s.assigned_user_id::text) as assigned_user_id,
        coalesce(u.display_name, u.full_name, u.email, '—') as manager_name,
        t.sla_due_at as sla_at,
        t.last_seen_at,
        case
            when t.sla_due_at is null then 'none'
            when t.sla_due_at < now() then 'red'
            when t.sla_due_at <= now() + interval '6 hours' then 'yellow'
            else 'green'
        end as sla_state
    from tasks t
    join stores s on s.id = t.store_id
    left join users u on u.id = coalesce(t.assigned_user_id, s.assigned_user_id)
    order by
        case when t.sla_due_at is null then 1 else 0 end,
        t.sla_due_at asc,
        t.created_at desc
    limit :limit offset :offset
    """)
    r = await db.execute(q, {"limit": limit, "offset": offset})
    return [dict(x) for x in r.mappings().all()]


@router.get("/tasks/summary")
async def tasks_summary(db: AsyncSession = Depends(get_db)):
    q = text("""
    select
        count(*) as total,
        count(*) filter (where coalesce(internal_status, 'new') = 'new') as new_count,
        count(*) filter (where coalesce(internal_status, 'new') = 'in_progress') as in_progress_count,
        count(*) filter (where coalesce(internal_status, 'new') = 'waiting') as waiting_count,
        count(*) filter (where coalesce(internal_status, 'new') = 'done') as done_count,
        count(*) filter (
            where sla_due_at is not null
              and sla_due_at < now()
              and coalesce(internal_status, 'new') <> 'done'
        ) as overdue_count
    from tasks
    """)
    row = (await db.execute(q)).mappings().first()
    return dict(row) if row else {
        "total": 0,
        "new_count": 0,
        "in_progress_count": 0,
        "waiting_count": 0,
        "done_count": 0,
        "overdue_count": 0,
    }


@router.post("/tasks/{task_id}/claim-auto")
async def claim_task_auto(task_id: str, db: AsyncSession = Depends(get_db)):
    q = text("""
    update tasks t
    set
        assigned_user_id = coalesce(t.assigned_user_id, s.assigned_user_id),
        accepted_at = coalesce(t.accepted_at, now()),
        internal_status = case
            when coalesce(t.internal_status, 'new') = 'done' then 'done'
            else 'in_progress'
        end
    from stores s
    where s.id = t.store_id
      and t.id::text = :task_id
    returning t.id::text as id
    """)
    row = (await db.execute(q, {"task_id": task_id})).mappings().first()
    await db.commit()

    if not row:
        return {"status": "error", "error": "Задача не найдена"}

    return {"status": "ok", "task_id": row["id"]}


@router.post("/tasks/{task_id}/work-status")
async def set_work_status(task_id: str, payload: TaskWorkStatusIn, db: AsyncSession = Depends(get_db)):
    allowed = {"new", "in_progress", "waiting", "done"}
    new_status = (payload.internal_status or "").strip()

    if new_status not in allowed:
        return {"status": "error", "error": "Недопустимый internal_status"}

    q = text("""
    update tasks t
    set
        internal_status = :internal_status,
        assigned_user_id = coalesce(t.assigned_user_id, s.assigned_user_id),
        accepted_at = case
            when :internal_status in ('in_progress', 'waiting', 'done')
                then coalesce(t.accepted_at, now())
            else t.accepted_at
        end,
        completed_at = case
            when :internal_status = 'done' then now()
            else null
        end
    from stores s
    where s.id = t.store_id
      and t.id::text = :task_id
    returning t.id::text as id
    """)
    row = (await db.execute(q, {"task_id": task_id, "internal_status": new_status})).mappings().first()
    await db.commit()

    if not row:
        return {"status": "error", "error": "Задача не найдена"}

    return {"status": "ok", "task_id": row["id"], "internal_status": new_status}
