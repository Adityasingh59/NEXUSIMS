"""NEXUS IMS — Async SQLAlchemy session and engine."""
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# ==========================
# FORCE ASYNC DRIVER SAFELY
# ==========================

raw_url = settings.DATABASE_URL
print("RAW DATABASE_URL:", raw_url)

url_obj = make_url(raw_url)

# Force asyncpg driver regardless of what Railway injects
url_obj = url_obj.set(drivername="postgresql+asyncpg")

final_url = str(url_obj)

print("FINAL ASYNC DATABASE_URL:", final_url)

engine = create_async_engine(
    final_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    tenant_id = getattr(request.state, "tenant_id", None)

    async with async_session_maker() as session:
        if tenant_id:
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
