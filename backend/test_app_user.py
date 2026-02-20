import asyncio
import asyncpg
import os

# Credentials for nexus_app
PG_USER = "nexus_app"
PG_PASS = "nexus_dev_password"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"

async def test_select():
    print(f"Connecting to '{TARGET_DB}' as {PG_USER}...")
    try:
        conn = await asyncpg.connect(
            user=PG_USER,
            password=PG_PASS,
            database=TARGET_DB,
            host=PG_HOST,
            port=PG_PORT
        )
        print("Connected!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    try:
        print("Attempting to call get_user_for_login...")
        rows = await conn.fetch("SELECT * FROM get_user_for_login($1)", "admin@nexus.com")
        print(f"Success! Rows: {rows}")
    except Exception as e:
        print(f"Function call failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_select())
