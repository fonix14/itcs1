import asyncio
from app.db import db_session
from app.services.dashboard_service import get_sla_metrics


async def main():
    async for session in db_session():
        data = await get_sla_metrics(session)
        print(data)
        break


if __name__ == "__main__":
    asyncio.run(main())
