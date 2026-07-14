-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for text search on alerts

-- Partial indexes for common queries
-- (SQLAlchemy will create main tables; these are performance extras)
