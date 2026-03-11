from __future__ import annotations
from arq import run_worker
from arq.connections import RedisSettings
from sqlalchemy import select
from app.settings import settings
from app.db import SessionLocal
from app.models import NotificationOutbox

async def process_outbox(_ctx):
    async with SessionLocal() as s:
        res = await s.execute(select(NotificationOutbox).where(NotificationOutbox.status=="pending").limit(50))
        items = res.scalars().all()
        if not items:
            return 0
        for n in items:
            n.attempts += 1
            n.last_error = "sender not implemented in stage1"
            if n.attempts >= 5:
                n.status = "failed"
        await s.commit()
        return len(items)

class WorkerSettings:
    functions = [process_outbox]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

if __name__ == "__main__":
    run_worker(WorkerSettings)
