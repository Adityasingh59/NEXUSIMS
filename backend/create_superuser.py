import asyncio
import uuid
from app.db.session import async_session_maker
from app.models.tenant import Tenant, User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_superuser():
    async with async_session_maker() as db:
        try:
            # 1. Check or Create Tenant
            print("Checking for existing tenant...")
            result = await db.execute(select(Tenant).where(Tenant.name == "NEXUS Default"))
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                print("Creating default tenant...")
                tenant = Tenant(
                    name="NEXUS Default",
                    slug="nexus-default"
                )
                db.add(tenant)
                await db.flush()
                print(f"Tenant created: {tenant.id}")
            else:
                print(f"Using existing tenant: {tenant.id}")

            # 2. Check or Create Admin User
            email = "admin@nexus.com"
            password = "admin"
            
            print(f"Checking for user {email}...")
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"Creating admin user {email}...")
                user = User(
                    email=email,
                    hashed_password=get_password_hash(password),
                    full_name="System Admin",
                    role="ADMIN",
                    tenant_id=tenant.id,
                    is_active=True
                )
                db.add(user)
                await db.commit()
                print(f"Superuser created successfully!")
                print(f"Email: {email}")
                print(f"Password: {password}")
            else:
                print("Admin user already exists.")
                
        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_superuser())
