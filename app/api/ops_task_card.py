from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

router = APIRouter(tags=["ops_task_card"])


@router.get("/api/ops/task-card/{task_id}")
async def task_card(task_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("""
            select
                t.*,
                s.store_no,
                s.name as store_name,
                coalesce(u.display_name, u.full_name, u.email, '—') as manager_name
            from tasks t
            left join stores s on s.id = t.store_id
            left join users u on u.id = coalesce(t.assigned_user_id, s.assigned_user_id)
            where t.id::text = :id
        """),
        {"id": task_id},
    )
    item = row.mappings().first()
    if not item:
        return {"status": "error", "error": "Задача не найдена"}
    return {"status": "ok", "data": dict(item)}
