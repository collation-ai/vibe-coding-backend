# PostgreSQL User Database Selection Fix

## Problem
When creating a PostgreSQL user from the admin dashboard, the database dropdown only showed a partial list of databases from existing `database_assignments`, not all databases available on the selected server.

The workflow was incorrect:
- ❌ **Before**: Database list was static, loaded from existing assignments
- ✅ **After**: Database list is dynamic, loaded from the selected server

## Solution
Implemented a proper workflow where:
1. User selects credential type (stored or custom)
2. User selects database server from dropdown
3. System automatically fetches and populates all databases from that server
4. User selects one or more databases from the populated list

## Changes Made

### 1. New API Endpoint (`api/admin.py`)

**Added:** `GET /api/admin/database-servers/{server_id}/databases` (line 933-994)

This endpoint:
- Connects to the selected database server
- Queries all non-system databases from `pg_database`
- Excludes system databases: `postgres`, `template0`, `template1`, `azure_maintenance`
- Returns a list of database names

```python
@router.get("/api/admin/database-servers/{server_id}/databases")
async def list_databases_on_server(server_id: str, ...):
    # Connect to postgres database
    # Query pg_database for all user databases
    # Return list of database names
```

### 2. Frontend JavaScript Updates (`admin/admin.js`)

#### Added `loadDatabasesFromServer()` function (line 613-644):
- Fetches databases from the selected server
- Shows loading state while fetching
- Populates the database dropdown with results
- Handles errors gracefully

#### Updated `showCreatePgUserModal()` (line 602-611):
- Removed automatic database loading
- Sets initial state to prompt user to select server first

#### Updated `togglePgCredentialInput()` (line 1028-1056):
- Resets database dropdown when credential type changes
- Shows appropriate message based on credential type

#### Added `onPgServerSelected()` (line 1059-1064):
- Event handler for server selection
- Automatically loads databases when server is selected

### 3. HTML Updates (`admin/index.html`)

**Line 467**: Added `onchange` event handler to server select:
```html
<select id="pg-stored-server" onchange="onPgServerSelected()"></select>
```

## User Workflow (After Fix)

### Create PostgreSQL User:
1. Click "Create PostgreSQL User"
2. Select Vibe user
3. Select credential type:
   - **Stored Credentials**:
     - Select database server → Databases auto-populate
     - Select database from populated list
   - **Custom Connection**:
     - Enter connection string manually
     - Database field shows informational message

### What the User Sees:

**Initial State:**
- Database dropdown: "Select a database server first"

**After Selecting Server:**
- Database dropdown: "Loading databases..." (briefly)
- Then: Full list of all databases on that server

**If Error:**
- Database dropdown: "Error loading databases"
- Toast notification with error message

## Database Query
The endpoint queries PostgreSQL system catalog:
```sql
SELECT datname
FROM pg_database
WHERE datistemplate = false
AND datname NOT IN ('postgres', 'template0', 'template1', 'azure_maintenance')
ORDER BY datname
```

This ensures only user databases are shown, not system databases.

## Benefits
1. ✅ **Complete List**: Shows ALL databases on the server, not just assigned ones
2. ✅ **Dynamic**: Updates when different servers are selected
3. ✅ **User-Friendly**: Auto-populates on server selection
4. ✅ **Accurate**: Queries directly from PostgreSQL catalog
5. ✅ **Fast**: Caches server credentials, single query to list databases

## Testing
To test the fix:
1. Go to http://localhost:8000/admin
2. Navigate to "PostgreSQL Users" tab
3. Click "Create PostgreSQL User"
4. Select "Use Stored Server Credentials"
5. Select a database server from dropdown
6. Verify database dropdown automatically populates with all databases
7. Select different servers to verify dynamic loading

## Related Files
- `/home/tanmais/vibe-coding-backend/api/admin.py` - New API endpoint
- `/home/tanmais/vibe-coding-backend/admin/admin.js` - Frontend logic
- `/home/tanmais/vibe-coding-backend/admin/index.html` - Event handler
