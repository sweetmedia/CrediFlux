-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas for multi-tenant architecture
CREATE SCHEMA IF NOT EXISTS public;
