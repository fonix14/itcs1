from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.services.mobile_manager_service import (
    list_mobile_tasks,
    get_mobile_task_card,
    accept_mobile_task,
    add_mobile_comment,
    list_task_attachments,
    add_task_attachment,
)
from app.settings import settings

router = APIRouter(tags=["mobile-manager"])


class TaskCommentIn(BaseModel):
    comment: str


class PushKeysIn(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=10)
    keys: PushKeysIn
    manager_user_id: str | None = None


async def _resolve_actor(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> tuple[str | None, str | None]:
    role = x_user_role.strip().lower() if isinstance(x_user_role, str) else None
    return x_user_id, role


def _build_kwargs(fn: Any, **kwargs: Any) -> dict[str, Any]:
    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in allowed}


async def _call_service(fn: Any, **kwargs: Any):
    return await fn(**_build_kwargs(fn, **kwargs))


async def _resolve_manager_user_id(session: AsyncSession, actor_user_id: str | None, payload_manager_user_id: str | None) -> str:
    if actor_user_id:
        return actor_user_id
    if payload_manager_user_id:
        return payload_manager_user_id
    row = (await session.execute(text("select id::text as id from users where role='manager' order by created_at asc limit 1"))).mappings().first()
    if not row:
        raise HTTPException(status_code=400, detail="No manager user found")
    return row["id"]


@router.get("/api/mobile/tasks")
async def api_mobile_tasks(
    limit: int = Query(default=100, ge=1, le=300),
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    try:
        actor_user_id, actor_role = actor
        data = await _call_service(
            list_mobile_tasks,
            session=session,
            limit=limit,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/api/mobile/tasks/{task_id}")
async def api_mobile_task_card(
    task_id: str,
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor
    data = await _call_service(
        get_mobile_task_card,
        session=session,
        task_id=task_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "data": data}


@router.post("/api/mobile/tasks/{task_id}/accept")
async def api_mobile_accept(
    task_id: str,
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor
    data = await _call_service(
        accept_mobile_task,
        session=session,
        task_id=task_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "data": data}


@router.post("/api/mobile/tasks/{task_id}/comment")
async def api_mobile_comment(
    task_id: str,
    payload: TaskCommentIn,
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor
    data = await _call_service(
        add_mobile_comment,
        session=session,
        task_id=task_id,
        comment=payload.comment,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "data": data}


@router.get("/api/tasks/{task_id}/attachments")
async def api_list_attachments(
    task_id: str,
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor
    data = await _call_service(
        list_task_attachments,
        session=session,
        task_id=task_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    return {"status": "ok", "data": data}


@router.post("/api/tasks/{task_id}/attachments")
async def api_add_attachment(
    task_id: str,
    file: UploadFile = File(...),
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    file_bytes = await file.read()
    if not file_bytes:
        return {"status": "error", "error": "empty file"}

    actor_user_id, actor_role = actor

    try:
        data = await _call_service(
            add_task_attachment,
            session=session,
            task_id=task_id,
            file_name=file.filename or "photo.jpg",
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
        if data is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/api/mobile/push/config")
async def api_push_config():
    return {
        "status": "ok",
        "data": {
            "vapid_public_key": settings.vapid_public_key or "",
            "push_enabled": bool(settings.vapid_public_key and settings.vapid_private_key),
        },
    }


@router.post("/api/mobile/push/subscribe")
async def api_push_subscribe(
    payload: PushSubscriptionIn,
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, _ = actor
    manager_user_id = await _resolve_manager_user_id(session, actor_user_id, payload.manager_user_id)
    try:
        await session.execute(
            text(
                """
                insert into device_subscriptions (id, user_id, endpoint, p256dh, auth, is_active, created_at)
                values (gen_random_uuid(), cast(:user_id as uuid), :endpoint, :p256dh, :auth, true, now())
                on conflict (endpoint) do update
                set user_id = cast(:user_id as uuid),
                    p256dh = excluded.p256dh,
                    auth = excluded.auth,
                    is_active = true
                """
            ),
            {
                "user_id": manager_user_id,
                "endpoint": payload.endpoint,
                "p256dh": payload.keys.p256dh,
                "auth": payload.keys.auth,
            },
        )
        await session.commit()
        return {"status": "ok", "message": "subscription saved", "manager_user_id": manager_user_id}
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}


@router.post("/api/mobile/push/unsubscribe")
async def api_push_unsubscribe(
    endpoint: str,
    session: AsyncSession = Depends(db_session),
):
    try:
        await session.execute(text("update device_subscriptions set is_active=false where endpoint=:endpoint"), {"endpoint": endpoint})
        await session.commit()
        return {"status": "ok"}
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": str(e)}
