from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _safe_uuid(value: str) -> str:
    return str(uuid.UUID(str(value)))


async def get_mobile_task_card(
    session: AsyncSession,
    task_id: str,
    actor_user_id: str,
    actor_role: str,
) -> dict[str, Any]:
    task_id = _safe_uuid(task_id)

    task_sql = text("""
        select
            t.id::text as id,
            t.portal_task_id,
            t.status,
            coalesce(tis.internal_status, 'new') as internal_status,
            t.sla_due_at as sla,
            t.last_seen_at,
            s.store_no,
            s.name as store_name,
            s.address as store_address,
            coalesce(u.full_name, u.email, '—') as manager_name,
            u.email as manager_email
        from tasks t
        left join stores s on s.id = t.store_id
        left join task_internal_state tis on tis.task_id = t.id
        left join users u on u.id = s.assigned_user_id
        where t.id = cast(:task_id as uuid)
        limit 1
    """)

    task_row = (await session.execute(task_sql, {"task_id": task_id})).mappings().first()
    if not task_row:
        return {"task": None, "comments": []}

    comments_sql = text("""
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
        limit 50
    """)

    comment_rows = (await session.execute(comments_sql, {"task_id": task_id})).mappings().all()

    comments = [
        {
            "id": row["id"],
            "author_role": row["author_role"],
            "author_name": row["author_name"],
            "author_user_id": row["author_user_id"],
            "comment_text": row["comment_text"],
            "comment": row["comment_text"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in comment_rows
    ]

    task = {
        "id": task_row["id"],
        "portal_task_id": task_row["portal_task_id"],
        "status": task_row["status"],
        "internal_status": task_row["internal_status"],
        "sla": task_row["sla"].isoformat() if task_row["sla"] else None,
        "last_seen_at": task_row["last_seen_at"].isoformat() if task_row["last_seen_at"] else None,
        "store_no": task_row["store_no"],
        "store_name": task_row["store_name"],
        "store_address": task_row["store_address"],
        "manager_name": task_row["manager_name"],
        "manager_email": task_row["manager_email"],
        "comments_count": len(comments),
        "viewer_role": actor_role,
    }

    return {"task": task, "comments": comments}


async def add_mobile_task_comment(
    session: AsyncSession,
    task_id: str,
    actor_user_id: str,
    actor_role: str,
    comment: str,
) -> dict[str, Any]:
    task_id = _safe_uuid(task_id)
    actor_user_id = _safe_uuid(actor_user_id)

    sql = text("""
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
    """)

    row = (
        await session.execute(
            sql,
            {
                "task_id": task_id,
                "actor_user_id": actor_user_id,
                "comment": comment.strip(),
            },
        )
    ).mappings().first()

    await session.commit()

    return {"id": row["id"], "status": "ok"}
