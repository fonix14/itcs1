from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.services.minio_service import upload_bytes, presigned_get_url


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


def _task_access_clause(role: str) -> str:
    if role == "dispatcher":
        return ""
    return """
      and exists (
        select 1
        from stores s2
        where s2.id = t.store_id
          and s2.assigned_user_id = cast(:actor_user_id as uuid)
      )
    """


async def list_mobile_tasks(session, actor_user_id: str, actor_role: str, limit: int = 100):
    access_clause = _task_access_clause(actor_role)

    rows = await _rows(
        session,
        f"""
        select
            t.id::text as id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        where 1=1
        {access_clause}
        order by
            case when t.sla is null then 1 else 0 end,
            t.sla asc,
            t.id desc
        limit :limit
        """,
        {"limit": limit, "actor_user_id": actor_user_id},
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


async def get_mobile_task_card(session, actor_user_id: str, actor_role: str, task_id: str):
    access_clause = _task_access_clause(actor_role)

    task = await _one(
        session,
        f"""
        select
            t.id::text as id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            t.store_id::text as store_id,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        where t.id = cast(:task_id as uuid)
        {access_clause}
        """,
        {"task_id": task_id, "actor_user_id": actor_user_id},
    )
    if not task:
        return None

    events = await _rows(
        session,
        """
        select id::text as id, event_type, payload, created_at
        from task_events
        where task_id = cast(:task_id as uuid)
        order by id desc
        limit 20
        """,
        {"task_id": task_id},
    )

    attachments = await list_task_attachments(session, actor_user_id, actor_role, task_id)

    return {
        "id": task.get("id"),
        "portal_task_id": task.get("portal_task_id"),
        "status": task.get("status"),
        "sla": _to_iso(task.get("sla")),
        "last_seen_at": _to_iso(task.get("last_seen_at")),
        "store_id": task.get("store_id"),
        "store_no": task.get("store_no"),
        "manager_name": task.get("manager_name"),
        "events": [
            {
                "id": ev.get("id"),
                "event_type": ev.get("event_type"),
                "payload": ev.get("payload"),
                "created_at": _to_iso(ev.get("created_at")),
            }
            for ev in events
        ],
        "attachments": attachments,
    }


async def accept_mobile_task(session, actor_user_id: str, actor_role: str, task_id: str):
    task = await get_mobile_task_card(session, actor_user_id, actor_role, task_id)
    if not task:
        return None

    await _execute(
        session,
        """
        update tasks
        set status = 'accepted',
            last_seen_at = now()
        where id = cast(:task_id as uuid)
        """,
        {"task_id": task_id},
    )

    payload = json.dumps({"source": "mobile", "actor_user_id": actor_user_id}, ensure_ascii=False)
    await _execute(
        session,
        """
        insert into task_events (task_id, event_type, payload, created_at)
        values (cast(:task_id as uuid), 'ACCEPTED', cast(:payload as jsonb), now())
        """,
        {"task_id": task_id, "payload": payload},
    )

    return await get_mobile_task_card(session, actor_user_id, actor_role, task_id)


async def add_mobile_comment(session, actor_user_id: str, actor_role: str, task_id: str, comment: str):
    task = await get_mobile_task_card(session, actor_user_id, actor_role, task_id)
    if not task:
        return None

    payload = json.dumps({"comment": comment, "actor_user_id": actor_user_id}, ensure_ascii=False)
    await _execute(
        session,
        """
        insert into task_events (task_id, event_type, payload, created_at)
        values (cast(:task_id as uuid), 'COMMENT', cast(:payload as jsonb), now())
        """,
        {"task_id": task_id, "payload": payload},
    )

    return await get_mobile_task_card(session, actor_user_id, actor_role, task_id)


async def list_task_attachments(session, actor_user_id: str, actor_role: str, task_id: str):
    task = await get_mobile_task_card_min(session, actor_user_id, actor_role, task_id)
    if not task:
        return []

    rows = await _rows(
        session,
        """
        select id::text as id, task_id::text as task_id, file_name, content_type, object_key, file_size, uploaded_by::text as uploaded_by, created_at
        from task_attachments
        where task_id = cast(:task_id as uuid)
        order by created_at desc, id desc
        """,
        {"task_id": task_id},
    )

    items = []
    for row in rows:
        preview_url = None
        try:
            preview_url = presigned_get_url(row.get("object_key"))
        except Exception:
            preview_url = None

        items.append(
            {
                "id": row.get("id"),
                "task_id": row.get("task_id"),
                "file_name": row.get("file_name"),
                "content_type": row.get("content_type"),
                "object_key": row.get("object_key"),
                "file_size": row.get("file_size"),
                "uploaded_by": row.get("uploaded_by"),
                "created_at": _to_iso(row.get("created_at")),
                "preview_url": preview_url,
            }
        )
    return items


async def get_mobile_task_card_min(session, actor_user_id: str, actor_role: str, task_id: str):
    access_clause = _task_access_clause(actor_role)
    return await _one(
        session,
        f"""
        select t.id::text as id
        from tasks t
        where t.id = cast(:task_id as uuid)
        {access_clause}
        """,
        {"task_id": task_id, "actor_user_id": actor_user_id},
    )


async def add_task_attachment(session, actor_user_id: str, actor_role: str, task_id: str, file_name: str, content_type: str, file_bytes: bytes):
    task = await get_mobile_task_card_min(session, actor_user_id, actor_role, task_id)
    if not task:
        return None

    ext = ""
    if "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[1].lower()

    object_key = f"tasks/{task_id}/{uuid.uuid4().hex}{ext}"
    upload_bytes(object_key=object_key, data=file_bytes, content_type=content_type)

    await _execute(
        session,
        """
        insert into task_attachments (task_id, file_name, content_type, object_key, file_size, created_at)
        values (cast(:task_id as uuid), :file_name, :content_type, :object_key, :file_size, now())
        """,
        {
            "task_id": task_id,
            "file_name": file_name,
            "content_type": content_type,
            "object_key": object_key,
            "file_size": len(file_bytes),
        },
    )

    payload = json.dumps({"file_name": file_name, "object_key": object_key, "actor_user_id": actor_user_id}, ensure_ascii=False)
    await _execute(
        session,
        """
        insert into task_events (task_id, event_type, payload, created_at)
        values (cast(:task_id as uuid), 'PHOTO_ADDED', cast(:payload as jsonb), now())
        """,
        {"task_id": task_id, "payload": payload},
    )

    return await list_task_attachments(session, actor_user_id, actor_role, task_id)
