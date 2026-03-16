from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text


TERMINAL_INTERNAL_STATUSES = ("closed", "resolved", "cancelled")


def _to_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _rows(session, sql: str, params: dict[str, Any] | None = None):
    res = await session.execute(text(sql), params or {})
    return [dict(x) for x in res.mappings().all()]


async def _one(session, sql: str, params: dict[str, Any] | None = None):
    res = await session.execute(text(sql), params or {})
    row = res.mappings().first()
    return dict(row) if row else None


async def _execute(session, sql: str, params: dict[str, Any] | None = None):
    await session.execute(text(sql), params or {})
    await session.commit()


async def _ensure_workflow_schema(session):
    await session.execute(text("create extension if not exists pgcrypto"))
    await session.execute(text("""
        create table if not exists task_internal_state (
            task_id uuid primary key references tasks(id) on delete cascade,
            internal_status text not null default 'new',
            accepted_at timestamptz null,
            accepted_by uuid null references users(id),
            closed_at timestamptz null,
            closed_by uuid null references users(id),
            manager_comment text null,
            updated_at timestamptz not null default now()
        )
    """))
    await session.execute(text("""
        create table if not exists task_comments (
            id uuid primary key default gen_random_uuid(),
            task_id uuid not null references tasks(id) on delete cascade,
            created_by uuid null references users(id),
            comment_text text not null,
            created_at timestamptz not null default now()
        )
    """))
    await session.execute(text("""
        create table if not exists task_events (
            id uuid primary key default gen_random_uuid(),
            task_id uuid not null references tasks(id) on delete cascade,
            event_type text not null,
            payload jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now()
        )
    """))
    await session.execute(text("create index if not exists ix_task_comments_task_id_created_at on task_comments(task_id, created_at desc)"))
    await session.execute(text("create index if not exists ix_task_events_task_id_created_at on task_events(task_id, created_at desc)"))
    await session.commit()


async def list_tasks(session, overdue_only: bool = False, limit: int = 100):
    await _ensure_workflow_schema(session)

    where_clause = ""
    if overdue_only:
        where_clause = """
        where coalesce(t.sla, t.sla_due_at) is not null
          and coalesce(tis.internal_status, 'new') not in ('closed', 'resolved', 'cancelled')
          and coalesce(t.sla, t.sla_due_at) < now()
        """

    rows = await _rows(
        session,
        f"""
        select
            t.id::text as id,
            t.portal_task_id,
            t.status as portal_status,
            coalesce(tis.internal_status, 'new') as internal_status,
            coalesce(t.sla, t.sla_due_at) as sla,
            t.last_seen_at,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        left join task_internal_state tis on tis.task_id = t.id
        {where_clause}
        order by
            case when coalesce(t.sla, t.sla_due_at) is null then 1 else 0 end,
            coalesce(t.sla, t.sla_due_at) asc,
            t.created_at desc
        limit :limit
        """,
        {"limit": limit},
    )

    return [
        {
            "id": row.get("id"),
            "portal_task_id": row.get("portal_task_id"),
            "portal_status": row.get("portal_status"),
            "internal_status": row.get("internal_status"),
            "status": row.get("internal_status") or row.get("portal_status"),
            "sla": _to_iso(row.get("sla")),
            "last_seen_at": _to_iso(row.get("last_seen_at")),
            "store_no": row.get("store_no"),
            "manager_name": row.get("manager_name"),
        }
        for row in rows
    ]


async def get_task_card(session, task_id: str):
    await _ensure_workflow_schema(session)

    task = await _one(
        session,
        """
        select
            t.id::text as id,
            t.portal_task_id,
            t.status as portal_status,
            coalesce(tis.internal_status, 'new') as internal_status,
            coalesce(t.sla, t.sla_due_at) as sla,
            t.last_seen_at,
            t.created_at,
            t.store_id::text as store_id,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name,
            tis.accepted_at,
            tis.closed_at,
            tis.manager_comment
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        left join task_internal_state tis on tis.task_id = t.id
        where t.id::text = :task_id
        """,
        {"task_id": task_id},
    )
    if not task:
        return None

    comments = await _rows(
        session,
        """
        select
            c.id::text as id,
            c.comment_text,
            c.created_at,
            coalesce(u.full_name, u.email, '—') as author_name
        from task_comments c
        left join users u on u.id = c.created_by
        where c.task_id::text = :task_id
        order by c.created_at desc
        limit 50
        """,
        {"task_id": task_id},
    )

    events = await _rows(
        session,
        """
        select
            id::text as id,
            event_type,
            payload,
            created_at
        from task_events
        where task_id::text = :task_id
        order by created_at desc
        limit 50
        """,
        {"task_id": task_id},
    )

    return {
        "id": task.get("id"),
        "portal_task_id": task.get("portal_task_id"),
        "portal_status": task.get("portal_status"),
        "internal_status": task.get("internal_status"),
        "status": task.get("internal_status") or task.get("portal_status"),
        "sla": _to_iso(task.get("sla")),
        "last_seen_at": _to_iso(task.get("last_seen_at")),
        "created_at": _to_iso(task.get("created_at")),
        "store_id": task.get("store_id"),
        "store_no": task.get("store_no"),
        "manager_name": task.get("manager_name"),
        "accepted_at": _to_iso(task.get("accepted_at")),
        "closed_at": _to_iso(task.get("closed_at")),
        "manager_comment": task.get("manager_comment"),
        "comments": [
            {
                "id": c.get("id"),
                "comment_text": c.get("comment_text"),
                "author_name": c.get("author_name"),
                "created_at": _to_iso(c.get("created_at")),
            }
            for c in comments
        ],
        "events": [
            {
                "id": e.get("id"),
                "event_type": e.get("event_type"),
                "payload": e.get("payload"),
                "created_at": _to_iso(e.get("created_at")),
            }
            for e in events
        ],
    }


async def add_task_comment(session, task_id: str, comment: str):
    await _ensure_workflow_schema(session)
    task = await _one(session, "select id::text as id from tasks where id::text = :task_id", {"task_id": task_id})
    if not task:
        return None

    payload = json.dumps({"comment": comment}, ensure_ascii=False)

    await session.execute(
        text(
            """
            insert into task_comments (task_id, comment_text, created_at)
            values (cast(:task_id as uuid), :comment, now())
            """
        ),
        {"task_id": task_id, "comment": comment},
    )

    await session.execute(
        text(
            """
            insert into task_events (task_id, event_type, payload, created_at)
            values (cast(:task_id as uuid), 'comment_added', cast(:payload as jsonb), now())
            """
        ),
        {"task_id": task_id, "payload": payload},
    )
    await session.commit()

    return await get_task_card(session, task_id)


async def accept_task(session, task_id: str):
    await _ensure_workflow_schema(session)
    task = await _one(session, "select id::text as id from tasks where id::text = :task_id", {"task_id": task_id})
    if not task:
        return None

    await session.execute(
        text(
            """
            insert into task_internal_state (task_id, internal_status, accepted_at, updated_at)
            values (cast(:task_id as uuid), 'accepted', now(), now())
            on conflict (task_id) do update
            set internal_status = 'accepted',
                accepted_at = coalesce(task_internal_state.accepted_at, now()),
                updated_at = now()
            """
        ),
        {"task_id": task_id},
    )

    await session.execute(
        text(
            """
            insert into task_events (task_id, event_type, payload, created_at)
            values (cast(:task_id as uuid), 'accepted', '{"source":"desktop_ui"}'::jsonb, now())
            """
        ),
        {"task_id": task_id},
    )
    await session.commit()

    return await get_task_card(session, task_id)


async def close_task(session, task_id: str, comment: str | None = None):
    await _ensure_workflow_schema(session)
    task = await _one(session, "select id::text as id from tasks where id::text = :task_id", {"task_id": task_id})
    if not task:
        return None

    await session.execute(
        text(
            """
            insert into task_internal_state (task_id, internal_status, closed_at, manager_comment, updated_at)
            values (cast(:task_id as uuid), 'resolved', now(), :comment, now())
            on conflict (task_id) do update
            set internal_status = 'resolved',
                closed_at = now(),
                manager_comment = coalesce(:comment, task_internal_state.manager_comment),
                updated_at = now()
            """
        ),
        {"task_id": task_id, "comment": comment},
    )

    if comment:
        await session.execute(
            text(
                """
                insert into task_comments (task_id, comment_text, created_at)
                values (cast(:task_id as uuid), :comment, now())
                """
            ),
            {"task_id": task_id, "comment": comment},
        )

    payload = json.dumps({"comment": comment}, ensure_ascii=False)
    await session.execute(
        text(
            """
            insert into task_events (task_id, event_type, payload, created_at)
            values (cast(:task_id as uuid), 'resolved', cast(:payload as jsonb), now())
            """
        ),
        {"task_id": task_id, "payload": payload},
    )
    await session.commit()

    return await get_task_card(session, task_id)
