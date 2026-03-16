from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.services.mobile_task_workflow_service import (
    accept_task,
    add_comment,
    close_task,
    get_task_detail,
)

router = APIRouter(tags=["mobile-task-workflow"])
templates = Jinja2Templates(directory="app/templates")


class CommentIn(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)


class CloseIn(BaseModel):
    comment: str | None = Field(default=None, max_length=5000)


def _require_actor(user_id: str | None, role: str | None) -> tuple[str, str]:
    if not user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header is required")
    return user_id, role or "manager"



@router.get("/api/mobile/task/{task_id}")
async def api_mobile_task_detail(
    task_id: UUID,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default="manager", alias="X-User-Role"),
):
    actor_user_id, actor_role = _require_actor(x_user_id, x_user_role)
    data = await get_task_detail(str(task_id), actor_user_id, actor_role)
    return {"status": "ok", "data": data}


@router.post("/api/mobile/task/{task_id}/accept")
async def api_mobile_task_accept(
    task_id: UUID,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default="manager", alias="X-User-Role"),
):
    actor_user_id, actor_role = _require_actor(x_user_id, x_user_role)
    data = await accept_task(str(task_id), actor_user_id, actor_role)
    return {"status": "ok", "data": data}


@router.post("/api/mobile/task/{task_id}/comment")
async def api_mobile_task_comment(
    task_id: UUID,
    payload: CommentIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default="manager", alias="X-User-Role"),
):
    actor_user_id, actor_role = _require_actor(x_user_id, x_user_role)
    data = await add_comment(str(task_id), payload.comment, actor_user_id, actor_role)
    return {"status": "ok", "data": data}


@router.post("/api/mobile/task/{task_id}/close")
async def api_mobile_task_close(
    task_id: UUID,
    payload: CloseIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default="manager", alias="X-User-Role"),
):
    actor_user_id, actor_role = _require_actor(x_user_id, x_user_role)
    data = await close_task(str(task_id), payload.comment, actor_user_id, actor_role)
    return {"status": "ok", "data": data}
