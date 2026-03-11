from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text


def _to_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _rows(session, sql: str, params: dict[str, Any] | None = None):
    try:
        res = await session.execute(text(sql), params or {})
        return [dict(x) for x in res.mappings().all()]
    except Exception:
        return []


async def _one(session, sql: str, params: dict[str, Any] | None = None):
    try:
        res = await session.execute(text(sql), params or {})
        row = res.mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


async def _execute(session, sql: str, params: dict[str, Any] | None = None):
    await session.execute(text(sql), params or {})
    await session.commit()


async def list_tasks(session, overdue_only: bool = False, limit: int = 100):
    where_clause = ""
    if overdue_only:
        where_clause = """
        where t.sla is not null
          and t.status not in ('done', 'closed', 'resolved', 'cancelled')
          and t.sla < now()
        """

    rows = await _rows(
        session,
        f"""
        select
            t.id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        {where_clause}
        order by
            case when t.sla is null then 1 else 0 end,
            t.sla asc,
            t.id desc
        limit :limit
        """,
        {"limit": limit},
    )

    return [
        {
            "id": row.get("id"),
            "portal_task_id": row.get("portal_task_id"),
            "status": row.get("status"),
            "sla": _to_iso(row.get("sla")),
            "last_seen_at": _to_iso(row.get("last_seen_at")),
            "store_no": row.get("store_no"),
            "manager_name": row.get("manager_name"),
        }
        for row in rows
    ]


async def get_task_card(session, task_id: int):
    task = await _one(
        session,
        """
        select
            t.id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            t.store_id,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        where t.id = :task_id
        """,
        {"task_id": task_id},
    )
    if not task:
        return None

    events = await _rows(
        session,
        """
        select
            id,
            event_type,
            payload,
            created_at
        from task_events
        where task_id = :task_id
        order by id desc
        limit 30
        """,
        {"task_id": task_id},
    )

    normalized_events = [
        {
            "id": event.get("id"),
            "event_type": event.get("event_type"),
            "payload": event.get("payload"),
            "created_at": _to_iso(event.get("created_at")),
        }
        for event in events
    ]

    return {
        "id": task.get("id"),
        "portal_task_id": task.get("portal_task_id"),
        "status": task.get("status"),
        "sla": _to_iso(task.get("sla")),
        "last_seen_at": _to_iso(task.get("last_seen_at")),
        "store_id": task.get("store_id"),
        "store_no": task.get("store_no"),
        "manager_name": task.get("manager_name"),
        "events": normalized_events,
    }


async def add_task_comment(session, task_id: int, comment: str):
    task = await _one(session, "select id from tasks where id = :task_id", {"task_id": task_id})
    if not task:
        return None

    payload = json.dumps({"comment": comment}, ensure_ascii=False)

    await _execute(
        session,
        """
        insert into task_events (task_id, event_type, payload, created_at)
        values (:task_id, 'COMMENT', cast(:payload as jsonb), now())
        """,
        {"task_id": task_id, "payload": payload},
    )

    return await get_task_card(session, task_id)


async def accept_task(session, task_id: int):
    task = await _one(session, "select id from tasks where id = :task_id", {"task_id": task_id})
    if not task:
        return None

    await _execute(
        session,
        """
        update tasks
        set status = 'accepted',
            last_seen_at = now()
        where id = :task_id
        """,
        {"task_id": task_id},
    )

    await _execute(
        session,
        """
        insert into task_events (task_id, event_type, payload, created_at)
        values (:task_id, 'ACCEPTED', '{"source":"ui"}'::jsonb, now())
        """,
        {"task_id": task_id},
    )

    return await get_task_card(session, task_id)
