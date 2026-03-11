from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/tasks")
async def tasks(limit: int = 200, offset: int = 0, db: AsyncSession = Depends(get_db)):
    q = text("""
        SELECT
            t.id,
            t.portal_task_id,
            s.store_no,
            t.status,
            t.sla_due_at,
            t.last_seen_at
        FROM tasks t
        JOIN stores s ON s.id = t.store_id
        ORDER BY t.sla_due_at ASC NULLS LAST, t.last_seen_at DESC
        LIMIT :limit OFFSET :offset
    """)
    r = await db.execute(q, {"limit": limit, "offset": offset})
    return [dict(x) for x in r.mappings()]
