from __future__ import annotations

import os
import platform
import socket
import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_dispatcher
from app.db import db_session

router = APIRouter(
    prefix="/api/admin",
    tags=["admin_server_overview"],
    dependencies=[Depends(require_dispatcher)],
)


def bytes_to_gb(value: int | float) -> float:
    return round(float(value) / 1024 / 1024 / 1024, 2)


def fmt_uptime(seconds: float) -> str:
    total = int(seconds)
    days = total // 86400
    hours = (total % 86400) // 3600
    minutes = (total % 3600) // 60
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    return f"{hours}ч {minutes}м"


@router.get("/server/overview")
async def admin_server_overview(
    session: AsyncSession = Depends(db_session),
):
    started = time.time()
    db_ok = True
    db_error = None

    try:
        await session.execute(text("select 1"))
    except Exception as e:
        db_ok = False
        db_error = str(e)

    try:
        vm = psutil.virtual_memory()
        du = psutil.disk_usage("/")
        boot_ts = psutil.boot_time()

        cpu_percent = psutil.cpu_percent(interval=0.25)
        per_cpu = psutil.cpu_percent(interval=None, percpu=True)

        process = psutil.Process(os.getpid())
        rss = process.memory_info().rss

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

        load_avg = None
        try:
            la = os.getloadavg()
            load_avg = [round(x, 2) for x in la]
        except Exception:
            load_avg = None

        data = {
            "status": "ok",
            "server_time_utc": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu": {
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
                "usage_percent": round(cpu_percent, 1),
                "per_cpu_percent": [round(x, 1) for x in per_cpu],
                "load_avg": load_avg,
            },
            "ram": {
                "total_gb": bytes_to_gb(vm.total),
                "used_gb": bytes_to_gb(vm.used),
                "available_gb": bytes_to_gb(vm.available),
                "usage_percent": round(vm.percent, 1),
            },
            "disk": {
                "mount": "/",
                "total_gb": bytes_to_gb(du.total),
                "used_gb": bytes_to_gb(du.used),
                "free_gb": bytes_to_gb(du.free),
                "usage_percent": round(du.percent, 1),
            },
            "api": {
                "status": "ok",
                "process_pid": process.pid,
                "process_rss_mb": round(rss / 1024 / 1024, 1),
                "response_ms": round((time.time() - started) * 1000, 1),
            },
            "db": {
                "status": "ok" if db_ok else "error",
                "error": db_error,
            },
            "uptime": {
                "boot_time": datetime.fromtimestamp(boot_ts, tz=timezone.utc).isoformat(),
                "uptime_seconds": int(time.time() - boot_ts),
                "uptime_human": fmt_uptime(time.time() - boot_ts),
            },
            "entity_counts": {
                "managers": int(managers_count or 0),
                "stores": int(stores_count or 0),
                "tasks": int(tasks_count or 0),
                "uploads": int(uploads_count or 0),
            },
        }
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}
