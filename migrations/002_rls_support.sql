-- Migration: Add Row-Level Security and Granular Permission Support
-- Version: 002
-- Description: Adds support for PostgreSQL user management, table-level permissions, and RLS policies

-- =====================================================
-- 1. PostgreSQL Database Users
-- =====================================================
-- Tracks PostgreSQL users created by the system for each Vibe user
CREATE TABLE IF NOT EXISTS pg_database_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vibe_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    pg_username VARCHAR(63) NOT NULL,  -- PostgreSQL max identifier length
    pg_password_encrypted TEXT NOT NULL,  -- Encrypted with Fernet
    connection_string_encrypted TEXT NOT NULL,  -- Full connection string with user credentials
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),  -- Admin who created this
    notes TEXT,  -- Optional notes
    UNIQUE(vibe_user_id, database_name),
    UNIQUE(database_name, pg_username)
);

CREATE INDEX idx_pg_database_users_vibe_user ON pg_database_users(vibe_user_id);
CREATE INDEX idx_pg_database_users_database ON pg_database_users(database_name);
CREATE INDEX idx_pg_database_users_pg_username ON pg_database_users(pg_username);

-- =====================================================
-- 2. Enhance Schema Permissions with DDL Controls
-- =====================================================
-- Add DDL permission columns to existing schema_permissions table
ALTER TABLE schema_permissions
    ADD COLUMN IF NOT EXISTS can_create_table BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS can_drop_table BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS can_alter_table BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS can_create_schema BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS apply_to_existing_tables BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS apply_to_future_tables BOOLEAN DEFAULT true;

-- Update existing permission values to new granular model
-- Convert old 'read_write' to individual permissions
UPDATE schema_permissions
SET
    can_create_table = true,
    can_drop_table = true,
    can_alter_table = true
WHERE permission = 'read_write';

-- =====================================================
-- 3. Table-Level Permissions
-- =====================================================
-- More granular than schema-level, allows per-table control
CREATE TABLE IF NOT EXISTS table_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vibe_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    can_select BOOLEAN DEFAULT false,
    can_insert BOOLEAN DEFAULT false,
    can_update BOOLEAN DEFAULT false,
    can_delete BOOLEAN DEFAULT false,
    can_truncate BOOLEAN DEFAULT false,
    can_references BOOLEAN DEFAULT false,  -- For foreign keys
    can_trigger BOOLEAN DEFAULT false,
    column_permissions JSONB,  -- Optional: column-level permissions {"col1": ["SELECT"], "col2": ["SELECT", "UPDATE"]}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    notes TEXT,
    UNIQUE(vibe_user_id, database_name, schema_name, table_name)
);

CREATE INDEX idx_table_permissions_vibe_user ON table_permissions(vibe_user_id);
CREATE INDEX idx_table_permissions_database ON table_permissions(database_name);
CREATE INDEX idx_table_permissions_table ON table_permissions(database_name, schema_name, table_name);

-- =====================================================
-- 4. RLS Policies
-- =====================================================
-- Tracks Row-Level Security policies applied to users
CREATE TABLE IF NOT EXISTS rls_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vibe_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,  -- Must be unique per table
    policy_type VARCHAR(20) NOT NULL CHECK (policy_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALL')),
    command_type VARCHAR(20),  -- PERMISSIVE or RESTRICTIVE
    using_expression TEXT,  -- SQL expression for USING clause (what rows user can see/modify)
    with_check_expression TEXT,  -- SQL expression for WITH CHECK clause (what rows user can insert/update to)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    template_used VARCHAR(100),  -- Name of template if used
    notes TEXT,
    UNIQUE(database_name, schema_name, table_name, policy_name)
);

CREATE INDEX idx_rls_policies_vibe_user ON rls_policies(vibe_user_id);
CREATE INDEX idx_rls_policies_table ON rls_policies(database_name, schema_name, table_name);
CREATE INDEX idx_rls_policies_active ON rls_policies(is_active);

-- =====================================================
-- 5. RLS Policy Templates
-- =====================================================
-- Pre-defined RLS policy templates for common use cases
CREATE TABLE IF NOT EXISTS rls_policy_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    policy_type VARCHAR(20) NOT NULL,
    using_expression_template TEXT NOT NULL,  -- With placeholders like {{user_column}}, {{user_value}}
    with_check_expression_template TEXT,
    required_columns JSONB,  -- Required columns in table for this template
    example_usage TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert common RLS templates
INSERT INTO rls_policy_templates (template_name, description, policy_type, using_expression_template, with_check_expression_template, required_columns, example_usage) VALUES
('user_owns_row', 'User can only access rows where they are the owner', 'ALL',
 '{{owner_column}} = current_user',
 '{{owner_column}} = current_user',
 '["owner_column"]',
 'Use when table has a user_id or owner column'),

('user_tenant_isolation', 'User can only access rows from their tenant', 'ALL',
 '{{tenant_column}} = ''{{tenant_value}}''',
 '{{tenant_column}} = ''{{tenant_value}}''',
 '["tenant_column"]',
 'Multi-tenant isolation by tenant_id'),

('user_region_filter', 'User can only access rows from their region', 'SELECT',
 '{{region_column}} IN ({{allowed_regions}})',
 NULL,
 '["region_column"]',
 'Regional data access control'),

('user_department_access', 'User can access rows from their department', 'ALL',
 '{{department_column}} = ''{{user_department}}''',
 '{{department_column}} = ''{{user_department}}''',
 '["department_column"]',
 'Department-based access control'),

('read_only_own_data', 'User can only read their own data, no modifications', 'SELECT',
 '{{user_column}} = current_user',
 NULL,
 '["user_column"]',
 'Read-only access to user-specific rows'),

('manager_sees_team', 'Manager can see all rows where they are the manager', 'SELECT',
 '{{manager_column}} = current_user OR {{employee_column}} = current_user',
 NULL,
 '["manager_column", "employee_column"]',
 'Hierarchical access - managers see their reports'),

('time_based_access', 'User can only access recent data', 'SELECT',
 '{{date_column}} >= NOW() - INTERVAL ''{{days}} days''',
 NULL,
 '["date_column"]',
 'Time-restricted access to data');

-- =====================================================
-- 6. Audit Log Enhancements
-- =====================================================
-- Add columns to track permission changes
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS permission_type VARCHAR(50),  -- 'schema', 'table', 'rls'
    ADD COLUMN IF NOT EXISTS permission_details JSONB,  -- Details of permission granted/revoked
    ADD COLUMN IF NOT EXISTS pg_username VARCHAR(63);  -- PostgreSQL user involved

-- =====================================================
-- 7. Database Server Credentials
-- =====================================================
-- Store admin credentials for each database server (from .env)
CREATE TABLE IF NOT EXISTS database_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_name VARCHAR(255) UNIQUE NOT NULL,  -- Friendly name
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 5432,
    admin_username VARCHAR(255) NOT NULL,
    admin_password_encrypted TEXT NOT NULL,
    ssl_mode VARCHAR(20) DEFAULT 'require',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_database_servers_active ON database_servers(is_active);

-- =====================================================
-- 8. User Settings
-- =====================================================
-- Store user-specific settings for permission behavior
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vibe_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    default_apply_to_existing_tables BOOLEAN DEFAULT true,
    default_apply_to_future_tables BOOLEAN DEFAULT true,
    auto_enable_rls BOOLEAN DEFAULT false,  -- Auto-enable RLS when granting table permissions
    settings JSONB,  -- Additional settings as needed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- Comments for Documentation
-- =====================================================
COMMENT ON TABLE pg_database_users IS 'PostgreSQL users created by Vibe system for granular access control';
COMMENT ON TABLE table_permissions IS 'Table-level permissions, more granular than schema-level';
COMMENT ON TABLE rls_policies IS 'Row-Level Security policies for fine-grained access control';
COMMENT ON TABLE rls_policy_templates IS 'Pre-defined RLS policy templates for common patterns';
COMMENT ON TABLE database_servers IS 'Database server admin credentials for user provisioning';
COMMENT ON TABLE user_settings IS 'User-specific permission behavior settings';

COMMENT ON COLUMN rls_policies.using_expression IS 'SQL expression for USING clause - determines which rows are visible';
COMMENT ON COLUMN rls_policies.with_check_expression IS 'SQL expression for WITH CHECK clause - validates new/updated rows';
COMMENT ON COLUMN rls_policies.command_type IS 'PERMISSIVE (OR logic) or RESTRICTIVE (AND logic) - default is PERMISSIVE';
