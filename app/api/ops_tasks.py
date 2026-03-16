from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.tasks_ui_service import list_tasks

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/tasks_legacy_disabled")
async def list_tasks_ops(db: AsyncSession = Depends(get_db)):
    data = await list_tasks(session=db, overdue_only=False, limit=200)
    return data
