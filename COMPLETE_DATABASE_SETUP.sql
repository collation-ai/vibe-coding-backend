-- Complete Database Setup for Vibe Coding Backend with Auth Gateway
-- This script ensures all required tables exist for both the API and auth gateway
-- Run this on your Azure PostgreSQL master database

-- Note: Azure Database for PostgreSQL has different UUID function names
-- Using gen_random_uuid() which is built-in for Azure PostgreSQL

-- ====================================
-- USERS TABLE (Required for Auth Gateway)
-- ====================================
-- Modified to include both username and password_hash for new auth system
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE,  -- Optional for backward compatibility
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),    -- Optional for backward compatibility
    organization VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Add username and password_hash columns if they don't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='username') THEN
        ALTER TABLE users ADD COLUMN username VARCHAR(255) UNIQUE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='password_hash') THEN
        ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
    END IF;
END $$;

-- ====================================
-- API KEYS TABLE (For backward compatibility)
-- ====================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- ====================================
-- DATABASE ASSIGNMENTS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS database_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    connection_string_encrypted TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, database_name)
);

-- ====================================
-- SCHEMA PERMISSIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS schema_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255) NOT NULL,
    permission VARCHAR(20) NOT NULL CHECK (permission IN ('read_only', 'read_write')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, database_name, schema_name)
);

-- ====================================
-- AUDIT LOGS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    database_name VARCHAR(255),
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    operation VARCHAR(50),
    request_body JSONB,
    response_status INTEGER,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ====================================
-- INDEXES FOR PERFORMANCE
-- ====================================
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_schema_permissions_user_id ON schema_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_database_assignments_user_id ON database_assignments(user_id);

-- ====================================
-- UPDATE TRIGGER FUNCTION
-- ====================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================================
-- TRIGGERS FOR UPDATED_AT
-- ====================================
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_schema_permissions_updated_at ON schema_permissions;
CREATE TRIGGER update_schema_permissions_updated_at 
    BEFORE UPDATE ON schema_permissions
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- INSERT DEFAULT API KEYS FOR TESTING
-- ====================================
-- Only insert if no api_keys exist
-- These are for backward compatibility with existing API keys
INSERT INTO users (id, email, username, organization, is_active)
SELECT 
    '00000000-0000-0000-0000-000000000001'::UUID,
    'dev@vibe-coding.com',
    'dev_user',  -- Adding username for compatibility
    'Vibe Coding Dev',
    true
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'dev@vibe-coding.com');

INSERT INTO users (id, email, username, organization, is_active)
SELECT 
    '00000000-0000-0000-0000-000000000002'::UUID,
    'prod@vibe-coding.com',
    'prod_user',  -- Adding username for compatibility
    'Vibe Coding Prod',
    true
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'prod@vibe-coding.com');

-- Insert dev API key
INSERT INTO api_keys (user_id, key_hash, key_prefix, name, is_active)
SELECT 
    '00000000-0000-0000-0000-000000000001'::UUID,
    -- This is the hash for vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA
    'hashed_vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA',
    'vibe_dev',
    'Development API Key',
    true
WHERE NOT EXISTS (SELECT 1 FROM api_keys WHERE key_prefix = 'vibe_dev');

-- Insert prod API key  
INSERT INTO api_keys (user_id, key_hash, key_prefix, name, is_active)
SELECT 
    '00000000-0000-0000-0000-000000000002'::UUID,
    -- This is the hash for vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ
    'hashed_vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ',
    'vibe_prod',
    'Production API Key',
    true
WHERE NOT EXISTS (SELECT 1 FROM api_keys WHERE key_prefix = 'vibe_prod');

-- ====================================
-- GRANT PERMISSIONS (Azure specific)
-- ====================================
-- Grant necessary permissions to the application user
-- Replace 'your_app_user' with your actual application database user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- ====================================
-- VERIFICATION QUERIES
-- ====================================
-- Run these to verify everything is set up correctly:

-- Check all tables exist:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('users', 'api_keys', 'database_assignments', 'schema_permissions', 'audit_logs')
ORDER BY table_name;

-- Check users table has all required columns:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Check if default API keys are inserted:
SELECT u.email, ak.key_prefix, ak.name, ak.is_active
FROM api_keys ak
JOIN users u ON ak.user_id = u.id;

-- Check indexes:
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('users', 'api_keys', 'database_assignments', 'schema_permissions', 'audit_logs')
ORDER BY tablename, indexname;