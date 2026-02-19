-- NEXUS IMS — Database Init Script
-- Creates nexus_app (INSERT-only on stock_ledger) and nexus_admin roles
-- Run as postgres superuser on first container start

-- Create nexus_admin role (for migrations)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nexus_admin') THEN
    CREATE ROLE nexus_admin WITH LOGIN PASSWORD 'nexus_dev_password';
  END IF;
END
$$;

-- Create nexus_app role (application runtime — restricted permissions)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nexus_app') THEN
    CREATE ROLE nexus_app WITH LOGIN PASSWORD 'nexus_dev_password';
  END IF;
END
$$;

-- Grant nexus_admin full access
GRANT ALL PRIVILEGES ON DATABASE nexus_ims TO nexus_admin;
GRANT ALL ON SCHEMA public TO nexus_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nexus_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nexus_admin;

-- Grant nexus_app connect
GRANT CONNECT ON DATABASE nexus_ims TO nexus_app;
GRANT USAGE ON SCHEMA public TO nexus_app;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: stock_ledger INSERT-only, UPDATE/DELETE revoked — applied in migration
-- Note: nexus_app gets table grants per migration; stock_ledger gets explicit INSERT-only
