from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text

try:
    from app.services.minio_service import upload_bytes, presigned_get_url
except Exception:  # pragma: no cover
    upload_bytes = None
    presigned_get_url = None


UUID_ZERO = "00000000-0000-0000-0000-000000000000"


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


async def _ensure_task_visible(session, task_id: str, actor_user_id: str | None, actor_role: str | None):
    sql = """
        select t.id
        from tasks t
        join stores s on s.id = t.store_id
        where t.id = cast(:task_id as uuid)
    """
    params: dict[str, Any] = {"task_id": task_id}
    if actor_user_id and actor_role != "dispatcher":
        sql += " and s.assigned_user_id = cast(:actor_user_id as uuid)"
        params["actor_user_id"] = actor_user_id
    return await _one(session, sql, params)


async def _resolve_actor_name(session, actor_user_id: str | None):
    if not actor_user_id:
        return "Менеджер"
    row = await _one(
        session,
        "select coalesce(full_name, email, 'Менеджер') as name from users where id = cast(:id as uuid)",
        {"id": actor_user_id},
    )
    return row["name"] if row else "Менеджер"


async def list_mobile_tasks(
    session,
    limit: int = 100,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    sql = """
        select
            t.id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name,
            tis.internal_status,
            tis.accepted_at,
            tis.accepted_by
        from tasks t
        left join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        left join task_internal_state tis on tis.task_id = t.id
        where 1=1
    """
    params: dict[str, Any] = {"limit": limit}
    if actor_user_id and actor_role != "dispatcher":
        sql += " and s.assigned_user_id = cast(:actor_user_id as uuid)"
        params["actor_user_id"] = actor_user_id
    sql += """
        order by
            case when t.sla is null then 1 else 0 end,
            t.sla asc,
            t.last_seen_at desc,
            t.id desc
        limit :limit
    """

    rows = await _rows(session, sql, params)
    items = []
    for row in rows:
        items.append(
            {
                "id": str(row.get("id")),
                "portal_task_id": row.get("portal_task_id"),
                "status": row.get("status"),
                "sla": _to_iso(row.get("sla")),
                "last_seen_at": _to_iso(row.get("last_seen_at")),
                "store_no": row.get("store_no"),
                "manager_name": row.get("manager_name"),
                "internal_status": row.get("internal_status") or "new",
                "accepted_at": _to_iso(row.get("accepted_at")),
                "accepted_by": str(row.get("accepted_by")) if row.get("accepted_by") else None,
            }
        )
    return items


async def list_task_attachments(
    session,
    task_id: str,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    visible = await _ensure_task_visible(session, task_id, actor_user_id, actor_role)
    if not visible:
        return []

    try:
        rows = await _rows(
            session,
            """
            select id, task_id, file_name, content_type, object_key, file_size, uploaded_by, created_at
            from task_attachments
            where task_id = cast(:task_id as uuid)
            order by created_at desc
            """,
            {"task_id": task_id},
        )
    except Exception:
        return []

    items = []
    for row in rows:
        preview_url = None
        if presigned_get_url and row.get("object_key"):
            try:
                preview_url = presigned_get_url(row.get("object_key"))
            except Exception:
                preview_url = None
        items.append(
            {
                "id": str(row.get("id")),
                "task_id": str(row.get("task_id")),
                "file_name": row.get("file_name"),
                "content_type": row.get("content_type"),
                "object_key": row.get("object_key"),
                "file_size": row.get("file_size"),
                "uploaded_by": str(row.get("uploaded_by")) if row.get("uploaded_by") else None,
                "created_at": _to_iso(row.get("created_at")),
                "preview_url": preview_url,
            }
        )
    return items


async def get_mobile_task_card(
    session,
    task_id: str,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    sql = """
        select
            t.id,
            t.portal_task_id,
            t.status,
            t.sla,
            t.last_seen_at,
            t.store_id,
            s.store_no,
            coalesce(u.full_name, u.email, '—') as manager_name,
            tis.internal_status,
            tis.accepted_at,
            tis.accepted_by,
            au.full_name as accepted_by_name
        from tasks t
        join stores s on s.id = t.store_id
        left join users u on u.id = s.assigned_user_id
        left join task_internal_state tis on tis.task_id = t.id
        left join users au on au.id = tis.accepted_by
        where t.id = cast(:task_id as uuid)
    """
    params: dict[str, Any] = {"task_id": task_id}
    if actor_user_id and actor_role != "dispatcher":
        sql += " and s.assigned_user_id = cast(:actor_user_id as uuid)"
        params["actor_user_id"] = actor_user_id
    task = await _one(session, sql, params)
    if not task:
        return None

    comments = await _rows(
        session,
        """
        select c.id, c.comment, c.author_role, c.author_user_id, c.created_at,
               coalesce(u.full_name, u.email, 'Менеджер') as author_name
        from task_comments c
        left join users u on u.id = c.author_user_id
        where c.task_id = cast(:task_id as uuid)
        order by c.created_at desc
        limit 50
        """,
        {"task_id": task_id},
    )

    events = await _rows(
        session,
        """
        select id, event_type, payload, created_at
        from task_events
        where task_id = cast(:task_id as uuid)
        order by created_at desc
        limit 50
        """,
        {"task_id": task_id},
    )

    attachments = await list_task_attachments(session, task_id, actor_user_id, actor_role)

    return {
        "id": str(task.get("id")),
        "portal_task_id": task.get("portal_task_id"),
        "status": task.get("status"),
        "sla": _to_iso(task.get("sla")),
        "last_seen_at": _to_iso(task.get("last_seen_at")),
        "store_id": str(task.get("store_id")),
        "store_no": task.get("store_no"),
        "manager_name": task.get("manager_name"),
        "internal_status": task.get("internal_status") or "new",
        "accepted_at": _to_iso(task.get("accepted_at")),
        "accepted_by": str(task.get("accepted_by")) if task.get("accepted_by") else None,
        "accepted_by_name": task.get("accepted_by_name") or None,
        "comments": [
            {
                "id": str(x.get("id")),
                "comment": x.get("comment"),
                "author_role": x.get("author_role"),
                "author_user_id": str(x.get("author_user_id")) if x.get("author_user_id") else None,
                "author_name": x.get("author_name"),
                "created_at": _to_iso(x.get("created_at")),
            }
            for x in comments
        ],
        "events": [
            {
                "id": str(x.get("id")),
                "event_type": x.get("event_type"),
                "payload": x.get("payload"),
                "created_at": _to_iso(x.get("created_at")),
            }
            for x in events
        ],
        "attachments": attachments,
    }


async def accept_mobile_task(
    session,
    task_id: str,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    visible = await _ensure_task_visible(session, task_id, actor_user_id, actor_role)
    if not visible:
        return None

    author_name = await _resolve_actor_name(session, actor_user_id)
    internal_status = "accepted"
    event_payload = json.dumps(
        {
            "source": "mobile",
            "actor_user_id": actor_user_id,
            "actor_role": actor_role or "manager",
            "author_name": author_name,
        },
        ensure_ascii=False,
    )

    await _execute(
        session,
        """
        insert into task_internal_state (task_id, internal_status, accepted_by, accepted_at, updated_at)
        values (
            cast(:task_id as uuid),
            :internal_status,
            cast(nullif(:actor_user_id, :zero_uuid) as uuid),
            now(),
            now()
        )
        on conflict (task_id) do update
        set internal_status = excluded.internal_status,
            accepted_by = excluded.accepted_by,
            accepted_at = excluded.accepted_at,
            updated_at = now()
        """,
        {
            "task_id": task_id,
            "internal_status": internal_status,
            "actor_user_id": actor_user_id or UUID_ZERO,
            "zero_uuid": UUID_ZERO,
        },
    )

    await _execute(
        session,
        """
        insert into task_events (id, task_id, event_type, payload, created_at)
        values (cast(:id as uuid), cast(:task_id as uuid), 'ACCEPTED', cast(:payload as jsonb), now())
        """,
        {"id": str(uuid.uuid4()), "task_id": task_id, "payload": event_payload},
    )
    await session.commit()
    return await get_mobile_task_card(session, task_id, actor_user_id, actor_role)


async def add_mobile_comment(
    session,
    task_id: str,
    comment: str,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    visible = await _ensure_task_visible(session, task_id, actor_user_id, actor_role)
    if not visible:
        return None

    comment = (comment or "").strip()
    if not comment:
        return await get_mobile_task_card(session, task_id, actor_user_id, actor_role)

    author_name = await _resolve_actor_name(session, actor_user_id)
    payload = json.dumps(
        {
            "comment": comment,
            "source": "mobile",
            "actor_user_id": actor_user_id,
            "actor_role": actor_role or "manager",
            "author_name": author_name,
        },
        ensure_ascii=False,
    )

    await _execute(
        session,
        """
        insert into task_comments (id, task_id, author_user_id, author_role, comment, created_at)
        values (
            cast(:id as uuid),
            cast(:task_id as uuid),
            cast(nullif(:actor_user_id, :zero_uuid) as uuid),
            :actor_role,
            :comment,
            now()
        )
        """,
        {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "actor_user_id": actor_user_id or UUID_ZERO,
            "zero_uuid": UUID_ZERO,
            "actor_role": actor_role or "manager",
            "comment": comment,
        },
    )
    await _execute(
        session,
        """
        insert into task_events (id, task_id, event_type, payload, created_at)
        values (cast(:id as uuid), cast(:task_id as uuid), 'COMMENT', cast(:payload as jsonb), now())
        """,
        {"id": str(uuid.uuid4()), "task_id": task_id, "payload": payload},
    )
    await session.commit()
    return await get_mobile_task_card(session, task_id, actor_user_id, actor_role)


async def add_task_attachment(
    session,
    task_id: str,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
):
    visible = await _ensure_task_visible(session, task_id, actor_user_id, actor_role)
    if not visible:
        return None

    if upload_bytes is None:
        raise RuntimeError("MinIO service is not configured")

    ext = ""
    if "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[1].lower()
    object_key = f"tasks/{task_id}/{uuid.uuid4().hex}{ext}"

    upload_bytes(object_key=object_key, data=file_bytes, content_type=content_type)

    await _execute(
        session,
        """
        insert into task_attachments (id, task_id, file_name, content_type, object_key, file_size, uploaded_by, created_at)
        values (
            cast(:id as uuid),
            cast(:task_id as uuid),
            :file_name,
            :content_type,
            :object_key,
            :file_size,
            cast(nullif(:actor_user_id, :zero_uuid) as uuid),
            now()
        )
        """,
        {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "file_name": file_name,
            "content_type": content_type,
            "object_key": object_key,
            "file_size": len(file_bytes),
            "actor_user_id": actor_user_id or UUID_ZERO,
            "zero_uuid": UUID_ZERO,
        },
    )

    payload = json.dumps({"file_name": file_name, "object_key": object_key, "source": "mobile"}, ensure_ascii=False)
    await _execute(
        session,
        """
        insert into task_events (id, task_id, event_type, payload, created_at)
        values (cast(:id as uuid), cast(:task_id as uuid), 'PHOTO_ADDED', cast(:payload as jsonb), now())
        """,
        {"id": str(uuid.uuid4()), "task_id": task_id, "payload": payload},
    )
    await session.commit()
    return await list_task_attachments(session, task_id, actor_user_id, actor_role)
