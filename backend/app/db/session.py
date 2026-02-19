"""NEXUS IMS — Async SQLAlchemy session and engine."""
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    autoexpire=False,
)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: yield async DB session.
    Sets app.tenant_id for RLS when request has tenant context.
    """
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
