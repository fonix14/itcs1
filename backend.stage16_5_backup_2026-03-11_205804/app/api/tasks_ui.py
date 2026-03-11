from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.services.tasks_ui_service import (
    list_tasks,
    get_task_card,
    add_task_comment,
    accept_task,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks-ui"])


class TaskCommentIn(BaseModel):
    comment: str


@router.get("")
async def api_list_tasks(
    overdue_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
):
    try:
        data = await list_tasks(session=session, overdue_only=overdue_only, limit=limit)
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/{task_id}")
async def api_get_task(task_id: int, session: AsyncSession = Depends(db_session)):
    data = await get_task_card(session=session, task_id=task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "data": data}


@router.post("/{task_id}/comment")
async def api_add_comment(
    task_id: int,
    payload: TaskCommentIn,
    session: AsyncSession = Depends(db_session),
):
    try:
        data = await add_task_comment(session=session, task_id=task_id, comment=payload.comment)
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/{task_id}/accept")
async def api_accept_task(task_id: int, session: AsyncSession = Depends(db_session)):
    try:
        data = await accept_task(session=session, task_id=task_id)
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}
