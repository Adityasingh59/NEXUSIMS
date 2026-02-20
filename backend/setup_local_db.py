import asyncio
import asyncpg
import os

# Credentials from user / default
PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"

# Target DB/Roles
TARGET_DB = "nexus_ims"
ADMIN_ROLE = "nexus_admin"
ADMIN_PASS = "nexus_dev_password"
APP_ROLE = "nexus_app"
APP_PASS = "nexus_dev_password"

async def setup():
    # Connect to default 'postgres' database to create roles and target DB
    print(f"Connecting to 'postgres' database as {PG_USER}...")
    try:
        sys_conn = await asyncpg.connect(
            user=PG_USER,
            password=PG_PASS,
            database="postgres",
            host=PG_HOST,
            port=PG_PORT
        )
    except Exception as e:
        print(f"Failed to connect to postgres: {e}")
        return

    try:
        # 1. Create Roles
        print("Checking roles...")
        roles = await sys_conn.fetch("SELECT rolname FROM pg_roles WHERE rolname IN ($1, $2)", ADMIN_ROLE, APP_ROLE)
        existing_roles = {r['rolname'] for r in roles}

        if ADMIN_ROLE not in existing_roles:
            print(f"Creating role {ADMIN_ROLE}...")
            await sys_conn.execute(f"CREATE ROLE {ADMIN_ROLE} WITH LOGIN PASSWORD '{ADMIN_PASS}' CREATEDB")
        
        if APP_ROLE not in existing_roles:
            print(f"Creating role {APP_ROLE}...")
            await sys_conn.execute(f"CREATE ROLE {APP_ROLE} WITH LOGIN PASSWORD '{APP_PASS}'")

        # 2. Create Database
        print(f"Checking database {TARGET_DB}...")
        db_exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TARGET_DB)
        
        if not db_exists:
            print(f"Creating database {TARGET_DB}...")
            # CREATE DATABASE cannot run inside a transaction block
            # asyncpg connect creates a transaction by default? No, but execute might.
            # actually execute is fine usually, but let's see. 
            # asyncpgConnection.execute() is atomic but not explicitly a transaction block unless 'begin' used.
            # But CREATE DATABASE is special.
            await sys_conn.execute(f'CREATE DATABASE "{TARGET_DB}" OWNER "{ADMIN_ROLE}"')
            print(f"Database {TARGET_DB} created!")
        else:
            print(f"Database {TARGET_DB} already exists.")

    finally:
        await sys_conn.close()

    print("Setup complete.")

if __name__ == "__main__":
    asyncio.run(setup())
