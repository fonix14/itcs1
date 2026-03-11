from __future__ import annotations

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL")
MANAGER_USER_ID = os.getenv("MANAGER_USER_ID")

engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)

async def main():
    if not MANAGER_USER_ID:
        raise RuntimeError("MANAGER_USER_ID is required")
    async with Session() as s:
        await s.execute(text("""
            insert into notification_outbox (id, channel, recipient_address, template, payload, status, attempts, next_retry_at, dedupe_key, created_at)
            values (gen_random_uuid(), 'webpush', :recipient, 'manager_task_new', jsonb_build_object('manager_user_id', :recipient, 'task_id', null, 'portal_task_id', 'TEST', 'store_no', 'TEST', 'kind', 'new_task', 'text', 'Тестовое push уведомление'), 'queued', 0, now(), :dedupe_key, now())
        """), {"recipient": MANAGER_USER_ID, "dedupe_key": f"test:webpush:{MANAGER_USER_ID}"})
        await s.commit()
        print('queued')

asyncio.run(main())
