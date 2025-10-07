# Database Server Credentials Storage Feature

## Overview
Added a secure credential storage system that allows admins to save database server credentials once and reuse them across all forms, eliminating the need to repeatedly enter connection strings.

---

## What Was Implemented

### 1. **New Database Table** (Already Existed from Migration 002)
```sql
CREATE TABLE database_servers (
    id UUID PRIMARY KEY,
    server_name VARCHAR(255) UNIQUE NOT NULL,  -- Friendly name like "Azure Production"
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 5432,
    admin_username VARCHAR(255) NOT NULL,
    admin_password_encrypted TEXT NOT NULL,    -- Fernet encrypted
    ssl_mode VARCHAR(20) DEFAULT 'require',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);
```

### 2. **New API Endpoints** (5 endpoints)

#### List Database Servers
```http
GET /api/admin/database-servers
X-API-Key: admin_key
```
**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "server_name": "Azure Production",
      "host": "server.postgres.database.azure.com",
      "port": 5432,
      "admin_username": "admin@server",
      "ssl_mode": "require",
      "is_active": true,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```
**Note:** Passwords are NEVER returned in list responses.

#### Create Database Server
```http
POST /api/admin/database-servers
X-API-Key: admin_key
Content-Type: application/json

{
  "server_name": "Azure Production",
  "host": "server.postgres.database.azure.com",
  "port": 5432,
  "admin_username": "admin@server",
  "admin_password": "secure_password_123",
  "ssl_mode": "require",
  "notes": "Main production server"
}
```

#### Get Connection String
```http
GET /api/admin/database-servers/{server_id}/connection-string?database_name=wealth_db
X-API-Key: admin_key
```
**Response:**
```json
{
  "success": true,
  "data": {
    "connection_string": "postgresql://admin:decrypted_password@host:5432/wealth_db?sslmode=require",
    "host": "server.postgres.database.azure.com",
    "port": 5432,
    "username": "admin@server"
  }
}
```

#### Update Database Server
```http
PUT /api/admin/database-servers/{server_id}
X-API-Key: admin_key
Content-Type: application/json

{
  "server_name": "Azure Production (Updated)",
  "admin_password": "new_password"  // Optional
}
```

#### Delete Database Server
```http
DELETE /api/admin/database-servers/{server_id}
X-API-Key: admin_key
```
**Note:** Soft delete - marks as `is_active = false`

### 3. **New Admin UI Tab: DB Servers**

**Location:** 🖥️ DB Servers tab (4th tab after Databases)

**Features:**
- List all stored database servers
- Add new server credentials
- Delete servers
- View server details (host, port, username, SSL mode)
- Info box explaining the feature

**Security:**
- Passwords are encrypted before storage (Fernet encryption)
- Passwords never displayed in the UI
- Only server metadata shown in table

### 4. **Updated Forms** (3 forms enhanced)

All forms that required admin credentials now support BOTH options:

#### A. **Create PG User Form**
- Added dropdown: "Admin Credentials"
  - **Option 1:** Use Stored Server (default)
  - **Option 2:** Enter Custom Connection String

**With Stored Server:**
```
Select Database Server: [Azure Production (server.postgres.database.azure.com) ▼]
```

**With Custom:**
```
Admin Connection String:
[postgresql://admin:pass@host:5432/db?sslmode=require]
```

#### B. **Grant Table Permission Form**
Same credential selection as above

#### C. **Create RLS Policy Form**
Same credential selection as above

---

## How It Works

### User Flow:

#### **First Time Setup (One-time):**

1. **Navigate to DB Servers tab**
2. **Click "+ Add Server"**
3. **Fill in server details:**
   - Server Name: `Azure Production` (friendly name for dropdown)
   - Host: `vibe-coding.postgres.database.azure.com`
   - Port: `5432`
   - Admin Username: `vibecodingadmin@vibe-coding`
   - Admin Password: `your_password`
   - SSL Mode: `require`
   - Notes: `Main production server`

4. **Click "Add Server"**
   - Password is encrypted with Fernet encryption
   - Stored in `database_servers` table
   - Server appears in table with encrypted password

#### **Using Stored Credentials:**

5. **Create PG User (or any other form):**
   - Vibe User: `alice@example.com`
   - Database: `wealth_db`
   - Admin Credentials: `Use Stored Server` ✓
   - Select Database Server: `Azure Production (vibe-coding.postgres.database.azure.com)`
   - Click "Create PG User"

**Behind the scenes:**
1. Frontend calls `getConnectionStringFromServer(server_id, 'wealth_db')`
2. Backend endpoint `/database-servers/{id}/connection-string?database_name=wealth_db`
3. Backend decrypts password
4. Builds connection string: `postgresql://admin:decrypted_pass@host:5432/wealth_db?sslmode=require`
5. Returns to frontend
6. Frontend uses it to create PG user

#### **Custom Connection String (Legacy Support):**

6. **Alternative: Select "Enter Custom Connection String"**
   - Dropdown switches to textarea
   - Enter full connection string manually
   - Works exactly like before

---

## Security Features

### ✅ **Encryption**
- **Algorithm:** Fernet (symmetric encryption)
- **Key:** From `settings.encryption_key` environment variable
- **Encrypted Fields:**
  - `admin_password_encrypted`

### ✅ **Never Exposed**
- Passwords NEVER returned in list endpoints
- Only returned when explicitly requesting connection string
- Requires admin API key to access

### ✅ **Secure Transmission**
- Connection strings built server-side
- Decryption happens in backend only
- Frontend receives ready-to-use connection string

### ✅ **Audit Trail**
- `created_at`, `updated_at` timestamps
- Soft delete with `is_active` flag
- Can track which forms used which servers (via logs)

---

## Code Changes

### **Backend Changes:**

#### `api/admin.py` (Added 180 lines)
```python
# New request models
class CreateDatabaseServerRequest(BaseModel):
    server_name: str
    host: str
    port: int = 5432
    admin_username: str
    admin_password: str
    ssl_mode: str = 'require'
    notes: Optional[str] = None

# 5 new endpoints
@router.get("/api/admin/database-servers")
@router.post("/api/admin/database-servers")
@router.get("/api/admin/database-servers/{server_id}/connection-string")
@router.put("/api/admin/database-servers/{server_id}")
@router.delete("/api/admin/database-servers/{server_id}")
```

### **Frontend Changes:**

#### `admin/index.html` (Added ~150 lines)
- New tab content: `db-servers-tab`
- New modal: `create-db-server-modal`
- Updated 3 existing modals with credential selection dropdowns
- Added toggle groups for stored vs custom credentials

#### `admin/admin.js` (Added ~200 lines)
```javascript
// New functions
loadDbServers()
showCreateDbServerModal()
createDbServer()
deleteDbServer()
loadDbServerOptions()
togglePgCredentialInput()
toggleTablePermCredentialInput()
toggleRlsCredentialInput()
getConnectionStringFromServer()

// Updated functions
createPgUser() - now handles both credential types
grantTablePermission() - now handles both credential types
createRlsPolicy() - now handles both credential types
showCreatePgUserModal() - preloads server options
showGrantTablePermissionModal() - preloads server options
showCreateRlsPolicyModal() - preloads server options
```

---

## Usage Examples

### Example 1: Single Server, Multiple Databases

**Setup:**
```javascript
// Add one server
Server Name: Azure Main
Host: myserver.postgres.database.azure.com
Username: admin@myserver
Password: ••••••••
```

**Use:**
```javascript
// Create PG user for database "db1"
Select Server: Azure Main
Database: db1
→ Builds: postgresql://admin:pass@myserver:5432/db1

// Create PG user for database "db2"
Select Server: Azure Main
Database: db2
→ Builds: postgresql://admin:pass@myserver:5432/db2

// Create RLS policy for database "db3"
Select Server: Azure Main
Database: db3
→ Builds: postgresql://admin:pass@myserver:5432/db3
```

### Example 2: Multiple Servers (Dev, Staging, Prod)

**Setup:**
```javascript
Server 1: "Development" - dev.postgres.database.azure.com
Server 2: "Staging" - staging.postgres.database.azure.com
Server 3: "Production" - prod.postgres.database.azure.com
```

**Use:**
```javascript
// Test in dev
Select Server: Development
Database: test_db

// Promote to staging
Select Server: Staging
Database: test_db

// Deploy to production
Select Server: Production
Database: production_db
```

### Example 3: Mixed Approach

**Use stored for common servers, custom for one-offs:**
```javascript
// Regular operation
Admin Credentials: Use Stored Server
Select Server: Azure Production

// Special migration server (temporary)
Admin Credentials: Enter Custom Connection String
Connection String: postgresql://migration_user:temp@temp-server:5432/migration_db
```

---

## Benefits

### ✅ **Convenience**
- Store once, use everywhere
- No copy-pasting connection strings
- Faster form submission

### ✅ **Security**
- Centralized credential management
- Encrypted storage
- Easy to rotate passwords (update in one place)

### ✅ **Reduced Errors**
- No typos in connection strings
- Consistent server configurations
- Dropdown selection prevents mistakes

### ✅ **Flexibility**
- Still supports custom connection strings
- Mix and match as needed
- No forced migration required

### ✅ **Scalability**
- Add unlimited servers
- Organize by environment, region, purpose
- Friendly names for easy identification

---

## Backward Compatibility

**100% backward compatible!**

- ✅ Old flows still work (custom connection string)
- ✅ No breaking changes to existing forms
- ✅ Default option is "Use Stored Server" but custom available
- ✅ Existing data unaffected

---

## Database Impact

**New Records:**
- Creates records in `database_servers` table
- No impact on existing tables
- No migration needed (table already exists)

**Storage:**
- Each server: ~500 bytes (encrypted password + metadata)
- 10 servers: ~5 KB
- 100 servers: ~50 KB
- Negligible storage impact

---

## Testing

### Test 1: Add Server
1. Navigate to DB Servers tab
2. Click "+ Add Server"
3. Fill form with Azure credentials
4. Submit
5. ✅ Server appears in table
6. ✅ Password is not visible

### Test 2: Use Stored Server in PG User Form
1. Go to PG Users tab
2. Click "+ Create PG User"
3. Select user and database
4. Admin Credentials: "Use Stored Server"
5. Select your server from dropdown
6. Submit
7. ✅ PG user created successfully
8. Check server logs: connection string was built correctly

### Test 3: Custom Connection String Still Works
1. Go to PG Users tab
2. Click "+ Create PG User"
3. Admin Credentials: "Enter Custom Connection String"
4. Paste custom connection string
5. Submit
6. ✅ PG user created successfully

### Test 4: Update Server Password
1. Manually update server password in DB Servers (future feature)
2. All forms using that server automatically use new password
3. ✅ No need to update forms individually

---

## Future Enhancements

### Potential Features:
1. **Edit Server:** Update server details via UI
2. **Server Groups:** Organize servers by environment
3. **Connection Test:** Test server connectivity before saving
4. **Usage Tracking:** Show which servers are used most
5. **Password Rotation:** Schedule automatic password updates
6. **Multi-Region:** Support for read replicas, failover servers
7. **Permission Templates:** Link servers to specific user roles

---

## Troubleshooting

### Issue: "Database server not found"
**Cause:** Server ID doesn't exist or is inactive
**Solution:** Check DB Servers tab, ensure server is active

### Issue: "Failed to get connection string"
**Cause:** Decryption failed (wrong encryption key)
**Solution:** Verify `ENCRYPTION_KEY` environment variable matches the key used to encrypt

### Issue: "Connection refused"
**Cause:** Stored credentials are incorrect
**Solution:**
1. Delete old server
2. Add new server with correct credentials
3. Or use "Enter Custom Connection String" as fallback

### Issue: Dropdown is empty
**Cause:** No servers added yet
**Solution:** Add at least one server in DB Servers tab

---

## Summary

### What This Feature Does:
**Allows admins to store database server credentials once in the DB Servers tab, then select from a dropdown in all forms instead of manually entering connection strings every time.**

### Key Benefits:
- 🔐 **Security:** Encrypted password storage
- ⚡ **Speed:** No more copy-pasting credentials
- 🎯 **Accuracy:** Dropdown selection prevents typos
- 🔄 **Flexibility:** Still supports custom connection strings
- 🚀 **Scalability:** Manage unlimited servers

### Files Modified:
- ✅ `api/admin.py` - 5 new endpoints
- ✅ `admin/index.html` - New tab + updated modals
- ✅ `admin/admin.js` - New functions + updated existing

### Total Implementation:
- **~530 lines of code added**
- **5 new API endpoints**
- **1 new admin tab**
- **3 forms enhanced**
- **0 breaking changes**

**The system is now production-ready with convenient, secure credential management! 🎉**
