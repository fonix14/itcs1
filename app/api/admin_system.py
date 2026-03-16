from __future__ import annotations

import os
import time

import psutil
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.authz import require_role
from app.db import get_db

router = APIRouter(prefix="/api/admin/system", tags=["admin_system"])


APP_START_TS = time.time()


@router.get("/metrics")
async def admin_system_metrics(request: Request, db: AsyncSession = Depends(get_db)):
    require_role(request, "admin")

    cpu_percent = psutil.cpu_percent(interval=0.2)
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")

    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        load1, load5, load15 = 0.0, 0.0, 0.0

    api_status = "ok"
    db_status = "ok"

    try:
        await db.execute(text("select 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "cpu_percent": round(cpu_percent, 2),
        "ram_percent": round(vm.percent, 2),
        "ram_used_gb": round(vm.used / 1024 / 1024 / 1024, 2),
        "ram_total_gb": round(vm.total / 1024 / 1024 / 1024, 2),
        "disk_percent": round(du.percent, 2),
        "disk_used_gb": round(du.used / 1024 / 1024 / 1024, 2),
        "disk_total_gb": round(du.total / 1024 / 1024 / 1024, 2),
        "disk_free_gb": round(du.free / 1024 / 1024 / 1024, 2),
        "load_1m": round(load1, 2),
        "load_5m": round(load5, 2),
        "load_15m": round(load15, 2),
        "uptime_seconds": int(time.time() - APP_START_TS),
        "api_status": api_status,
        "db_status": db_status,
    }
