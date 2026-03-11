from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel
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

router = APIRouter(tags=["mobile-manager"])


class TaskCommentIn(BaseModel):
    comment: str


async def _resolve_actor(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> tuple[str | None, str | None]:
    role = (x_user_role or "manager").strip().lower() if isinstance(x_user_role, str) else "manager"
    return x_user_id, role


async def _call_service(fn: Any, **kwargs: Any):
    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    final_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    return await fn(**final_kwargs)


@router.get("/api/mobile/tasks")
async def api_mobile_tasks(
    limit: int = Query(default=100, ge=1, le=300),
    actor: tuple[str | None, str | None] = Depends(_resolve_actor),
    session: AsyncSession = Depends(db_session),
):
    actor_user_id, actor_role = actor
    try:
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
    actor_user_id, actor_role = actor
    file_bytes = await file.read()
    if not file_bytes:
        return {"status": "error", "error": "empty file"}

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
