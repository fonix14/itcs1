from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db_session
from app.services.dashboard_service import (
    get_dashboard_metrics,
    get_health_metrics,
    get_sla_metrics,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(session: AsyncSession = Depends(db_session)):
    try:
        data = await get_dashboard_metrics(session)
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/health")
async def dashboard_health(session: AsyncSession = Depends(db_session)):
    try:
        data = await get_health_metrics(session)
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/sla")
async def dashboard_sla(session: AsyncSession = Depends(db_session)):
    try:
        data = await get_sla_metrics(session)
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}
