import asyncio
import asyncpg

PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"

async def check_and_grant():
    print(f"Connecting to {TARGET_DB}...")
    conn = await asyncpg.connect(user=PG_USER, password=PG_PASS, database=TARGET_DB, host=PG_HOST, port=PG_PORT)
    
    try:
        # Check ownership
        tables = await conn.fetch("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public'")
        print("Tables:", tables)

        # Force grant everything
        print("Granting ALL to nexus_app...")
        await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nexus_app")
        await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nexus_app")
        await conn.execute("GRANT ALL PRIVILEGES ON SCHEMA public TO nexus_app")
        
        # Verify
        perms = await conn.fetch("SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_name = 'users'")
        print("Permissions on users table:", perms)

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_and_grant())
