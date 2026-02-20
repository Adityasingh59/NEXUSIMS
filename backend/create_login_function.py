import asyncio
import asyncpg
import os

# Connect as superuser (postgres)
PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"

# Use nexus_admin (who owns tables) for the function owner so it has access
FUNCTION_OWNER = "nexus_admin" 
APP_ROLE = "nexus_app"

SQL_CREATE_FUNC = f"""
CREATE OR REPLACE FUNCTION get_user_for_login(p_email TEXT)
RETURNS SETOF users
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT * FROM users WHERE email = p_email AND is_active = true;
$$;

ALTER FUNCTION get_user_for_login(TEXT) OWNER TO {FUNCTION_OWNER};

GRANT EXECUTE ON FUNCTION get_user_for_login(TEXT) TO {APP_ROLE};
"""

async def deploy():
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
        print("Deploying security definer function...")
        await conn.execute(SQL_CREATE_FUNC)
        print("Function deployed and permissions granted!")

    except Exception as e:
        print(f"Error deploying function: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(deploy())
