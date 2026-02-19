"""NEXUS IMS — Seed dev tenant and user for testing (run after migrations)."""
import asyncio
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker

# Use nexus_admin for migrations/seeding (has DDL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://nexus_admin:nexus_dev_password@localhost:5432/nexus_ims",
).replace("nexus_app", "nexus_admin")


async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if tenant exists
        result = await session.execute(text("SELECT id FROM tenants WHERE slug = 'dev' LIMIT 1"))
        row = result.scalar_one_or_none()
        if row:
            print("Dev tenant already exists. Skipping seed.")
            return

        # Create dev tenant
        tenant_result = await session.execute(
            text("""
                INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), 'Dev Tenant', 'dev', true, now(), now())
                RETURNING id
            """)
        )
        tenant_id = tenant_result.scalar_one()

        # Create dev user (password: dev123)
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)
        hashed = pwd.hash("dev123")

        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'admin@dev.local', :pw, 'Dev Admin', 'ADMIN', true, now(), now())
            """),
            {"tid": str(tenant_id), "pw": hashed}
        )
        await session.commit()
        print("Seeded dev tenant and admin@dev.local (password: dev123)")


if __name__ == "__main__":
    asyncio.run(seed())
