from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db

router = APIRouter(prefix="/api/ops", tags=["ops"])

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    stats = {}

    r = await db.execute(text("select count(*) from tasks"))
    stats["total_tasks"] = r.scalar()

    r = await db.execute(text("select count(*) from tasks where sla_due_at < now()"))
    stats["overdue"] = r.scalar()

    r = await db.execute(text("select count(*) from notification_outbox where status='dead'"))
    stats["dead_notifications"] = r.scalar()

    return stats