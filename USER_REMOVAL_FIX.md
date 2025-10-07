# User Removal Bug Fix

## Problem
When attempting to remove a user from the admin dashboard, the operation failed with a 500 Internal Server Error. Two issues were found:

### Issue 1: Incorrect Column Names
```
Failed to remove user: Error: Request failed
```

### Issue 2: Foreign Key Constraint Violation
```
Failed to remove user: update or delete on table "users" violates foreign key constraint "audit_logs_user_id_fkey" on table "audit_logs"
DETAIL: Key (id)=(ef6b5787-bab0-4354-a8c7-d81993661a19) is still referenced from table "audit_logs".
```

## Root Causes

### Cause 1: Wrong Column Name
The `remove_user.py` endpoint was using incorrect column names when querying the `table_permissions` table:
- Used: `user_id`
- Correct: `vibe_user_id`

According to the database schema (`migrations/002_rls_support.sql` line 56), the `table_permissions` table uses `vibe_user_id` as the foreign key column name, not `user_id`.

### Cause 2: Missing Foreign Key Cleanup
The `audit_logs` table has a foreign key to `users(id)` but **WITHOUT** `ON DELETE CASCADE`. This means when deleting a user, we must manually delete audit logs first to avoid constraint violations.

Other tables that needed manual cleanup:
- `audit_logs` - No cascade, needs manual deletion
- `api_keys` - Has cascade but better to delete explicitly
- `pg_database_users` - Has cascade but better to delete explicitly
- `rls_policies` - Has cascade but better to delete explicitly

## Changes Made

### File: `api/admin_endpoints/remove_user.py`

**Fix 1: Corrected Column Names**

**Line 239** - Fixed table permissions fetch query:
```python
# Before:
WHERE user_id = $1

# After:
WHERE vibe_user_id = $1
```

**Line 262** - Fixed table permissions deletion:
```python
# Before:
DELETE FROM table_permissions WHERE user_id = $1

# After:
DELETE FROM table_permissions WHERE vibe_user_id = $1
```

**Fix 2: Added Foreign Key Cleanup**

Added deletion of all dependent records before deleting the user (lines 295-345):

1. **Delete audit_logs** (line 295-306):
   ```python
   DELETE FROM audit_logs WHERE user_id = $1
   ```

2. **Delete api_keys** (line 308-319):
   ```python
   DELETE FROM api_keys WHERE user_id = $1
   ```

3. **Delete pg_database_users** (line 321-332):
   ```python
   DELETE FROM pg_database_users WHERE vibe_user_id = $1
   ```

4. **Delete rls_policies** (line 334-345):
   ```python
   DELETE FROM rls_policies WHERE vibe_user_id = $1
   ```

All deletions are wrapped in try-except blocks to handle cases where tables might not exist or records might not be present.

## Testing
The server auto-reloaded after the fix was applied. To test:

1. Go to the admin dashboard at http://localhost:8000/admin
2. Click "Remove User" on any user
3. Confirm the email address by typing the exact email
4. The user should be removed successfully with a summary of:
   - PostgreSQL users dropped
   - Schema permissions revoked
   - Table permissions revoked
   - RLS policies dropped
   - Databases affected

## Order of Deletion
The user removal now follows this order to avoid foreign key violations:

1. ✅ Table permissions (no FK dependencies)
2. ✅ Schema permissions (no FK dependencies)
3. ✅ Database assignments (has CASCADE but deleted explicitly)
4. ✅ **Audit logs** (CRITICAL - no CASCADE, must delete manually)
5. ✅ **API keys** (has CASCADE but deleted explicitly for clarity)
6. ✅ **PostgreSQL users** (has CASCADE but deleted explicitly)
7. ✅ **RLS policies** (has CASCADE but deleted explicitly)
8. ✅ User record (now has no dependencies)
9. ✅ User cleanup audit record (stores deleted user info)

## Why This Bug Occurred
The `table_permissions` table was added in migration `002_rls_support.sql` and uses the column name `vibe_user_id` for consistency with other permission tables (`pg_database_users`, `rls_policies`). However, the `remove_user.py` code was written assuming the column name was `user_id`, which is used in older tables like `schema_permissions`.

## Prevention
When working with database queries:
1. Always check the actual schema in the migration files
2. Use consistent column naming across all tables
3. Consider using an ORM or type-safe query builder to catch these errors at compile time

## Related Files
- `/home/tanmais/vibe-coding-backend/api/admin_endpoints/remove_user.py` - Fixed file
- `/home/tanmais/vibe-coding-backend/migrations/002_rls_support.sql` - Schema definition
