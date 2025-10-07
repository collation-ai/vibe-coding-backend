-- Migration: Password Management and User Cleanup
-- Version: 003
-- Description: Adds password reset tokens, password expiry tracking, and user cleanup features

-- =====================================================
-- 1. Password Reset Tokens
-- =====================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,  -- SHA-256 hash of reset token
    email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),  -- IPv6 compatible
    user_agent TEXT,
    CONSTRAINT token_not_expired CHECK (expires_at > created_at)
);

CREATE INDEX idx_password_reset_tokens_user ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_expires ON password_reset_tokens(expires_at);

-- =====================================================
-- 2. Enhance Users Table with Password Policy
-- =====================================================
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS password_reset_required BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;

-- Set initial password expiry for existing users (90 days from now)
UPDATE users
SET password_expires_at = NOW() + INTERVAL '90 days'
WHERE password_expires_at IS NULL;

-- =====================================================
-- 3. Password History (prevent password reuse)
-- =====================================================
CREATE TABLE IF NOT EXISTS password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_password_history_user ON password_history(user_id);
CREATE INDEX idx_password_history_created ON password_history(created_at DESC);

-- =====================================================
-- 4. Email Notification Log
-- =====================================================
CREATE TABLE IF NOT EXISTS email_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email_to VARCHAR(255) NOT NULL,
    email_type VARCHAR(50) NOT NULL,  -- password_reset, password_expiry_warning, etc.
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    sent_at TIMESTAMP,
    failed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    message_id VARCHAR(255)  -- Azure Communication Services message ID
);

CREATE INDEX idx_email_notifications_user ON email_notifications(user_id);
CREATE INDEX idx_email_notifications_type ON email_notifications(email_type);
CREATE INDEX idx_email_notifications_sent ON email_notifications(sent_at);

-- =====================================================
-- 5. User Cleanup Audit
-- =====================================================
CREATE TABLE IF NOT EXISTS user_cleanup_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    cleanup_type VARCHAR(50) NOT NULL,  -- 'full_removal', 'pg_users_only', 'permissions_only'
    performed_by UUID REFERENCES users(id),
    pg_users_dropped INTEGER DEFAULT 0,
    schema_permissions_revoked INTEGER DEFAULT 0,
    table_permissions_revoked INTEGER DEFAULT 0,
    rls_policies_dropped INTEGER DEFAULT 0,
    cleanup_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_cleanup_audit_user ON user_cleanup_audit(user_id);
CREATE INDEX idx_user_cleanup_audit_type ON user_cleanup_audit(cleanup_type);
CREATE INDEX idx_user_cleanup_audit_performed_by ON user_cleanup_audit(performed_by);

-- =====================================================
-- 6. Functions for Password Policy
-- =====================================================

-- Function to check if password is expired
CREATE OR REPLACE FUNCTION is_password_expired(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
        AND password_expires_at < NOW()
    );
END;
$$ LANGUAGE plpgsql;

-- Function to extend password expiry
CREATE OR REPLACE FUNCTION extend_password_expiry(p_user_id UUID, p_days INTEGER)
RETURNS TIMESTAMP AS $$
DECLARE
    new_expiry TIMESTAMP;
BEGIN
    UPDATE users
    SET password_expires_at = NOW() + (p_days || ' days')::INTERVAL,
        password_changed_at = NOW()
    WHERE id = p_user_id
    RETURNING password_expires_at INTO new_expiry;

    RETURN new_expiry;
END;
$$ LANGUAGE plpgsql;

-- Function to get users with expiring passwords (next N days)
CREATE OR REPLACE FUNCTION get_users_with_expiring_passwords(p_days INTEGER)
RETURNS TABLE (
    user_id UUID,
    email VARCHAR,
    password_expires_at TIMESTAMP,
    days_until_expiry INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.email,
        u.password_expires_at,
        EXTRACT(DAY FROM (u.password_expires_at - NOW()))::INTEGER
    FROM users u
    WHERE u.is_active = true
    AND u.password_expires_at BETWEEN NOW() AND (NOW() + (p_days || ' days')::INTERVAL)
    ORDER BY u.password_expires_at;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Comments for Documentation
-- =====================================================
COMMENT ON TABLE password_reset_tokens IS 'Stores password reset tokens with expiry and usage tracking';
COMMENT ON TABLE password_history IS 'Tracks password history to prevent reuse of recent passwords';
COMMENT ON TABLE email_notifications IS 'Log of all emails sent by the system';
COMMENT ON TABLE user_cleanup_audit IS 'Audit trail of user removals and permission cleanup';

COMMENT ON COLUMN password_reset_tokens.token_hash IS 'SHA-256 hash of the reset token - actual token never stored';
COMMENT ON COLUMN password_reset_tokens.used_at IS 'Timestamp when token was used - prevents reuse';
COMMENT ON COLUMN users.password_expires_at IS 'When password expires and user must reset';
COMMENT ON COLUMN users.password_reset_required IS 'Force password reset on next login';
COMMENT ON COLUMN users.locked_until IS 'Account locked until this timestamp due to failed login attempts';
