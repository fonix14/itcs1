from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security import get_actor

router = APIRouter(prefix="/api/task", tags=["task-single"])


class CommentIn(BaseModel):
    comment: str = Field(min_length=1, max_length=4000)


def _safe_uuid(value: str) -> str:
    return str(uuid.UUID(str(value)))


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    try:
        return v.isoformat()
    except Exception:
        return str(v)


@router.get("/{task_id}")
async def get_task_single(
    task_id: str,
    session: AsyncSession = Depends(get_db),
    actor=Depends(get_actor),
):
    try:
        task_id = _safe_uuid(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid task_id")

    try:
        actor_user_id, actor_role = actor
    except Exception:
        actor_user_id, actor_role = None, "manager"

    try:
        row = (
            await session.execute(
                text("""
                    select
                        t.id::text as id,
                        t.portal_task_id,
                        t.status,
                        coalesce(t.internal_status, 'new') as internal_status,
                        t.sla_due_at as sla_due_at,
                        t.last_seen_at,
                        s.store_no,
                        s.name as store_name,
                        s.address as store_address,
                        coalesce(u.full_name, u.email, '—') as manager_name,
                        u.email as manager_email
                    from tasks t
                    left join stores s on s.id = t.store_id
                    left join users u on u.id = s.assigned_user_id
                    where t.id = cast(:task_id as uuid)
                    limit 1
                """),
                {"task_id": task_id},
            )
        ).mappings().first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"task query failed: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="task not found")

    try:
        comments_count = (
            await session.execute(
                text("""
                    select count(*)
                    from task_comments
                    where task_id = cast(:task_id as uuid)
                """),
                {"task_id": task_id},
            )
        ).scalar_one()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"comments count failed: {e}")

    payload = {
        "id": row.get("id"),
        "portal_task_id": row.get("portal_task_id"),
        "status": row.get("status"),
        "internal_status": row.get("internal_status"),
        "sla": _iso(row.get("sla_due_at")),
        "last_seen_at": _iso(row.get("last_seen_at")),
        "store_no": row.get("store_no"),
        "store_name": row.get("store_name"),
        "store_address": row.get("store_address"),
        "manager_name": row.get("manager_name"),
        "manager_email": row.get("manager_email"),
        "comments_count": int(comments_count or 0),
        "viewer_role": actor_role or "manager",
        "viewer_name": str(actor_user_id) if actor_user_id else None,
    }

    return {"status": "ok", "data": payload}


@router.get("/{task_id}/comments")
async def get_task_comments(
    task_id: str,
    session: AsyncSession = Depends(get_db),
    actor=Depends(get_actor),
):
    try:
        task_id = _safe_uuid(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid task_id")

    rows = (
        await session.execute(
            text("""
                select
                    c.id::text as id,
                    'manager' as author_role,
                    coalesce(u.full_name, u.email, 'Менеджер') as author_name,
                    c.created_by::text as author_user_id,
                    c.comment_text as comment_text,
                    c.created_at
                from task_comments c
                left join users u on u.id = c.created_by
                where c.task_id = cast(:task_id as uuid)
                order by c.created_at desc
            """),
            {"task_id": task_id},
        )
    ).mappings().all()

    data = [
        {
            "id": r["id"],
            "author_role": r["author_role"],
            "author_name": r["author_name"],
            "author_user_id": r["author_user_id"],
            "comment_text": r["comment_text"],
            "comment": r["comment_text"],
            "created_at": _iso(r["created_at"]),
        }
        for r in rows
    ]

    return {"status": "ok", "data": data}


@router.post("/{task_id}/comments")
async def add_task_comment(
    task_id: str,
    payload: CommentIn,
    session: AsyncSession = Depends(get_db),
    actor=Depends(get_actor),
):
    try:
        actor_user_id, actor_role = actor
    except Exception:
        raise HTTPException(status_code=401, detail="actor not resolved")

    try:
        task_id = _safe_uuid(task_id)
        actor_user_id = _safe_uuid(actor_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid actor/task uuid")

    comment = (payload.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="comment is required")

    row = (
        await session.execute(
            text("""
                insert into task_comments (
                    id,
                    task_id,
                    created_by,
                    comment_text,
                    created_at
                )
                values (
                    gen_random_uuid(),
                    cast(:task_id as uuid),
                    cast(:actor_user_id as uuid),
                    :comment,
                    now()
                )
                returning id::text as id
            """),
            {
                "task_id": task_id,
                "actor_user_id": actor_user_id,
                "comment": comment,
            },
        )
    ).mappings().first()

    await session.commit()

    return {
        "status": "ok",
        "data": {
            "id": row["id"],
            "author_role": actor_role,
        },
    }
