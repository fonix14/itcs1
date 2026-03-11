from __future__ import annotations
import asyncio
from uuid import UUID
from sqlalchemy import text
from app.db import engine

DISPATCHER_ID = UUID("11111111-1111-1111-1111-111111111111")
MANAGER_ID    = UUID("22222222-2222-2222-2222-222222222222")

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
        insert into users(id,email,full_name,role,is_active)
        values
          (:d,'dispatcher@example.local','Dispatcher','dispatcher',true),
          (:m,'manager@example.local','Manager 1','manager',true)
        on conflict (email) do nothing
        """), {"d": str(DISPATCHER_ID), "m": str(MANAGER_ID)})

        for i in range(1, 5):
            store_no = f"{1000+i}"
            assigned = str(MANAGER_ID) if i <= 3 else None
            await conn.execute(text("""
            insert into stores(store_no,name,assigned_user_id)
            values (:no, :name, :uid)
            on conflict (store_no) do nothing
            """), {"no": store_no, "name": f"Store {store_no}", "uid": assigned})

        await conn.execute(text("""
        with s as (select id, store_no from stores)
        insert into tasks(portal_task_id, store_id, status, sla, last_seen_at, created_at)
        select 'PT-'||s.store_no||'-'||x.n, s.id, 'in_progress', 'major', now(), now()
        from s cross join (values (1),(2)) as x(n)
        on conflict (portal_task_id) do nothing
        """))

    print("Seeded demo data.")
    print("Dispatcher headers: X-User-Id=11111111-1111-1111-1111-111111111111, X-User-Role=dispatcher")
    print("Manager headers:    X-User-Id=22222222-2222-2222-2222-222222222222, X-User-Role=manager")

if __name__ == "__main__":
    asyncio.run(main())
