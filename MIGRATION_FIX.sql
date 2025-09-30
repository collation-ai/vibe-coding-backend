-- Migration Script to Fix Existing Database
-- Run this if you're getting NULL constraint errors

-- First, check if the users table exists and has data
SELECT COUNT(*) as existing_users FROM users;

-- Update existing users to have a username if they don't have one
-- Using email prefix as username
UPDATE users 
SET username = SPLIT_PART(email, '@', 1) || '_' || LEFT(id::text, 8)
WHERE username IS NULL;

-- If you already have users without usernames, you can also do:
UPDATE users 
SET username = CASE 
    WHEN email = 'dev@vibe-coding.com' THEN 'dev_user'
    WHEN email = 'prod@vibe-coding.com' THEN 'prod_user'
    ELSE SPLIT_PART(email, '@', 1) || '_' || LEFT(id::text, 8)
END
WHERE username IS NULL;

-- Verify no NULL usernames remain
SELECT id, email, username FROM users WHERE username IS NULL;

-- Now you can safely run the complete setup script