-- Vault Database Initialization
-- Run by PostgreSQL container on first start

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vault') THEN
        CREATE ROLE vault WITH LOGIN PASSWORD 'vault_secret';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE vault_db TO vault;
GRANT ALL ON SCHEMA public TO vault;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO vault;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO vault;
