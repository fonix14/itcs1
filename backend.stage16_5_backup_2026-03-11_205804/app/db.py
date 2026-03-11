import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields AsyncSession.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Backward compatibility (Stage 2.5 / notifier imports)
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Legacy alias for get_db() to avoid breaking older imports.
    """
    async for s in get_db():
        yield s
