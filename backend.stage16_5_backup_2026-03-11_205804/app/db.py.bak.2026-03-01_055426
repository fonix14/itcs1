from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def set_actor(session, user_id: str, role: str):
    await session.execute(
        text("select app.set_actor(CAST(:uid AS uuid), CAST(:role AS text))"),
        {"uid": user_id, "role": role},
    )

@asynccontextmanager
async def db_session(user_id: str | None, role: str | None):
    async with SessionLocal() as session:
        if user_id and role:
            await set_actor(session, user_id, role)
        yield session
