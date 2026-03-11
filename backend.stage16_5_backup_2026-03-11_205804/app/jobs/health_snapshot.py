
import asyncio
from sqlalchemy import text
from app.db import async_session

async def run():
    async with async_session() as session:
        try:
            r = await session.execute(text("SELECT count(*) FROM tasks"))
            tasks = r.scalar()

            r = await session.execute(text("SELECT count(*) FROM anomalies WHERE status='open'"))
            anomalies = r.scalar()

            print("Health snapshot")
            print("tasks:", tasks)
            print("open anomalies:", anomalies)

        except Exception as e:
            print("health error:", e)

if __name__ == "__main__":
    asyncio.run(run())
