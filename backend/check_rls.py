import asyncio
import asyncpg

PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"

async def check_rls():
    conn = await asyncpg.connect(user=PG_USER, password=PG_PASS, database=TARGET_DB, host=PG_HOST, port=PG_PORT)
    try:
        # Check RLS
        rows = await conn.fetch("SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'users'")
        print("RLS Status:", rows)
        
        # Check policies
        policies = await conn.fetch("SELECT * FROM pg_policy WHERE polrelid = 'users'::regclass")
        print("Policies:", policies)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_rls())
