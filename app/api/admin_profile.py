from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_dispatcher
from app.db import db_session

router = APIRouter(
    prefix="/api/admin",
    tags=["admin_profile"],
    dependencies=[Depends(require_dispatcher)],
)


@router.get("/profile")
async def admin_profile(
    user: dict = Depends(require_dispatcher),
    session: AsyncSession = Depends(db_session),
):
    try:
        managers_count = await session.scalar(
            text("select count(*) from users where role = 'manager' and is_active = true")
        )
        stores_count = await session.scalar(
            text("select count(*) from stores")
        )
        tasks_count = await session.scalar(
            text("select count(*) from tasks")
        )
        uploads_count = await session.scalar(
            text("select count(*) from uploads")
        )

        return {
            "status": "ok",
            "data": {
                "user_id": user.get("user_id"),
                "full_name": user.get("full_name"),
                "email": user.get("email"),
                "role": user.get("role"),
                "managers_count": int(managers_count or 0),
                "stores_count": int(stores_count or 0),
                "tasks_count": int(tasks_count or 0),
                "uploads_count": int(uploads_count or 0),
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
