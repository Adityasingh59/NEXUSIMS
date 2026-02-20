import asyncio
import asyncpg
import os

# Connect as superuser (postgres) to grant permissions
PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"
APP_ROLE = "nexus_app"

async def grant_perms():
    print(f"Connecting to '{TARGET_DB}' as {PG_USER}...")
    try:
        conn = await asyncpg.connect(
            user=PG_USER,
            password=PG_PASS,
            database=TARGET_DB,
            host=PG_HOST,
            port=PG_PORT
        )
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    try:
        print(f"Granting usage on schema public to {APP_ROLE}...")
        await conn.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE};")
        
        print(f"Granting SELECT, INSERT, UPDATE, DELETE on all tables to {APP_ROLE}...")
        await conn.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};")
        
        print(f"Granting USAGE, SELECT on all sequences to {APP_ROLE}...")
        await conn.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};")
        
        # Ensure future tables get these privileges too
        print("Setting default privileges...")
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};")
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE};")
        
        # Explicitly grant on users table to be sure
        await conn.execute(f"GRANT ALL ON TABLE users TO {APP_ROLE};")

        print("Permissions granted successfully!")

    except Exception as e:
        print(f"Error granting permissions: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(grant_perms())
