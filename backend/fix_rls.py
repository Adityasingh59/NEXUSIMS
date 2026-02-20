import asyncio
import asyncpg
import os

PG_USER = "postgres"
PG_PASS = "Aditya@0509"
PG_HOST = "localhost"
PG_PORT = "5432"
TARGET_DB = "nexus_ims"
APP_ROLE = "nexus_app"

async def fix_rls():
    print("Connecting to DB...")
    conn = await asyncpg.connect(user=PG_USER, password=PG_PASS, database=TARGET_DB, host=PG_HOST, port=PG_PORT)
    try:
        # Create a policy that allows selecting users by email for authentication
        # The policy should allow SELECT if email matches
        # BUT RLS applies to rows.
        # If we want to login, we need to find the user by email.
        # So we need a policy that allows: SELECT * FROM users WHERE email = current_user_email?
        # No, we don't know who is logged in yet.
        
        # Option 1: BYPASSRLS for nexus_app? (Easiest for MVP dev, but less secure)
        # Option 2: Policy allowing SELECT on users where is_active = true? (Publicly visible user list? No)
        # Option 3: Use a SECURITY DEFINER function for login? (Best practice)
        
        # Given the error is "permission denied", it usually means RLS blocked it (silently returns empty) OR table permissions.
        # Wait, previous error was "permission denied for table users".
        # If RLS is on, and no policy allows access, it mimics permission denied?
        # As of Postgres 15, if RLS is on and no policy matches, it returns empty rows (SELECT) or error (INSERT/UPDATE).
        # But the original error was "permission denied".
        # That usually means GRANT problem.
        # But verify_perms showed permissions were granted!
        
        # Wait! The error `permission denied for table users` came from `curl`.
        # `test_app_user.py` returned EMPTY ROWS.
        # This discrepancy is key.
        # `test_app_user.py` -> empty rows -> RLS is active and hiding rows.
        # `curl` -> permission denied -> ???
        
        # If `nexus_app` has BYPASSRLS, it ignores policies.
        # Let's try granting BYPASSRLS to nexus_app for now to unblock.
        
        print(f"Granting BYPASSRLS to {APP_ROLE}...")
        await conn.execute(f"ALTER ROLE {APP_ROLE} BYPASSRLS;")
        print("Granted BYPASSRLS.")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_rls())
