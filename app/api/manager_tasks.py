from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(prefix="/api/manager", tags=["manager_tasks"])


def require_manager(request: Request) -> tuple[str, str]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "manager":
        raise HTTPException(status_code=401, detail="Требуется вход менеджера")
    return user_id, role


class ManagerTaskStatusIn(BaseModel):
    internal_status: str


@router.get("/me")
async def manager_me(request: Request):
    user_id, _ = require_manager(request)
    return {
        "status": "ok",
        "id": user_id,
        "display_name": request.session.get("display_name", "Менеджер"),
    }


@router.get("/tasks")
async def manager_tasks(request: Request, db: AsyncSession = Depends(get_db)):
    manager_id, _ = require_manager(request)

    rows = await db.execute(text("""
        select
            t.id::text as id,
            t.portal_task_id,
            s.store_no,
            coalesce(t.status, 'open') as portal_status,
            coalesce(t.internal_status, 'new') as internal_status,
            t.sla_due_at as sla_at,
            t.last_seen_at,
            coalesce(u.display_name, u.full_name, u.email, '—') as manager_name,
            case
                when t.sla_due_at is null then 'none'
                when coalesce(t.internal_status, 'new') = 'done' then 'none'
                when t.sla_due_at < now() then 'overdue'
                when t.sla_due_at <= now() + interval '24 hours' then 'warning'
                else 'normal'
            end as risk_state
        from tasks t
        join stores s on s.id = t.store_id
        left join users u on u.id = coalesce(t.assigned_user_id, s.assigned_user_id)
        where coalesce(t.assigned_user_id, s.assigned_user_id)::text = :manager_id
        order by
            case
                when t.sla_due_at is null then 2
                when t.sla_due_at < now() then 0
                when t.sla_due_at <= now() + interval '24 hours' then 1
                else 2
            end asc,
            t.sla_due_at asc nulls last,
            t.created_at desc
    """), {"manager_id": manager_id})

    return {"status": "ok", "data": [dict(x) for x in rows.mappings().all()]}


@router.post("/tasks/{task_id}/claim")
async def manager_claim_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    manager_id, _ = require_manager(request)

    row = (
        await db.execute(text("""
            update tasks t
            set
                assigned_user_id = :manager_id,
                accepted_at = coalesce(t.accepted_at, now()),
                internal_status = 'in_progress'
            from stores s
            where s.id = t.store_id
              and t.id::text = :task_id
              and coalesce(t.assigned_user_id, s.assigned_user_id)::text = :manager_id
            returning t.id::text as id
        """), {
            "task_id": task_id,
            "manager_id": manager_id,
        })
    ).mappings().first()

    await db.commit()

    if not row:
        return {"status": "error", "error": "Задача недоступна"}

    return {"status": "ok", "task_id": row["id"], "internal_status": "in_progress"}


@router.post("/tasks/{task_id}/status")
async def manager_set_status(
    task_id: str,
    payload: ManagerTaskStatusIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    manager_id, _ = require_manager(request)
    allowed = {"in_progress", "waiting", "done"}
    new_status = (payload.internal_status or "").strip()

    if new_status not in allowed:
        return {"status": "error", "error": "Недопустимый статус"}

    row = (
        await db.execute(text("""
            update tasks t
            set
                assigned_user_id = :manager_id,
                internal_status = :internal_status,
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
              and coalesce(t.assigned_user_id, s.assigned_user_id)::text = :manager_id
            returning t.id::text as id
        """), {
            "task_id": task_id,
            "manager_id": manager_id,
            "internal_status": new_status,
        })
    ).mappings().first()

    await db.commit()

    if not row:
        return {"status": "error", "error": "Задача недоступна"}

    return {"status": "ok", "task_id": row["id"], "internal_status": new_status}
