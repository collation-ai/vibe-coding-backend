# User Management Guide

## Overview

This guide explains how to create and manage users, databases, and permissions for the Vibe Coding Backend.

## Quick Start

### Interactive Admin Console

The easiest way to manage users is through the interactive admin console:

```bash
source venv/bin/activate
python scripts/admin.py --interactive
```

This provides a menu-driven interface for all admin operations.

## User Management Workflow

### Step 1: Create a User

Every user needs an account in the system:

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 1: Create User

# Command line
python scripts/admin.py --create-user "user@example.com" --org "Company Name"
```

### Step 2: Generate API Key

Users need API keys to authenticate:

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 2: Generate API Key

# Command line
python scripts/admin.py --generate-key "user@example.com" --key-name "Production Key" --env prod
```

**Important**: Save the API key immediately - it cannot be retrieved again!

### Step 3: Create Database in PostgreSQL

Before assigning a database to a user, create it in PostgreSQL:

```sql
-- Connect to PostgreSQL
CREATE DATABASE user_db_001;

-- Or in Azure PostgreSQL
-- Use Azure Portal or Azure CLI to create the database
```

### Step 4: Assign Database to User

Connect the user to their database:

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 3: Assign Database

# Command line
python scripts/admin.py --assign-db "user@example.com" "user_db_001" \
  "postgresql://username:password@host:5432/user_db_001?sslmode=require"
```

### Step 5: Grant Permissions

Grant schema-level permissions:

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 4: Grant Permission

# Command line
# Grant read-write access to public schema
python scripts/admin.py --grant "user@example.com" "user_db_001" "public" "read_write"

# Grant read-only access to reports schema
python scripts/admin.py --grant "user@example.com" "user_db_001" "reports" "read_only"
```

## Permission Levels

- **read_only**: User can SELECT data only
- **read_write**: User can perform all operations (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, etc.)

## Common Scenarios

### Scenario 1: Developer Account

A developer needs full access to their development database:

```bash
# 1. Create user
python scripts/admin.py --create-user "dev@company.com" --org "Development"

# 2. Generate API key
python scripts/admin.py --generate-key "dev@company.com" --key-name "Dev Key" --env dev

# 3. Assign database
python scripts/admin.py --assign-db "dev@company.com" "dev_db" \
  "postgresql://dev:devpass@localhost:5432/dev_db?sslmode=require"

# 4. Grant full access
python scripts/admin.py --grant "dev@company.com" "dev_db" "public" "read_write"
```

### Scenario 2: Analytics User

An analyst needs read-only access to production data:

```bash
# 1. Create user
python scripts/admin.py --create-user "analyst@company.com" --org "Analytics"

# 2. Generate API key with expiration
python scripts/admin.py --generate-key "analyst@company.com" \
  --key-name "Analytics Key" --env prod

# 3. Assign database
python scripts/admin.py --assign-db "analyst@company.com" "prod_db" \
  "postgresql://readonly:pass@prod.host:5432/prod_db?sslmode=require"

# 4. Grant read-only access
python scripts/admin.py --grant "analyst@company.com" "prod_db" "public" "read_only"
```

### Scenario 3: Multi-Tenant Application

Different customers need isolated databases:

```bash
# Customer A
python scripts/admin.py --create-user "customer_a@app.com" --org "Customer A"
python scripts/admin.py --generate-key "customer_a@app.com" --key-name "Customer A API"
python scripts/admin.py --assign-db "customer_a@app.com" "customer_a_db" \
  "postgresql://user:pass@host:5432/customer_a_db?sslmode=require"
python scripts/admin.py --grant "customer_a@app.com" "customer_a_db" "public" "read_write"

# Customer B
python scripts/admin.py --create-user "customer_b@app.com" --org "Customer B"
python scripts/admin.py --generate-key "customer_b@app.com" --key-name "Customer B API"
python scripts/admin.py --assign-db "customer_b@app.com" "customer_b_db" \
  "postgresql://user:pass@host:5432/customer_b_db?sslmode=require"
python scripts/admin.py --grant "customer_b@app.com" "customer_b_db" "public" "read_write"
```

## Azure PostgreSQL Setup

### 1. Create Databases in Azure

```bash
# Using Azure CLI
az postgres db create \
  --resource-group myResourceGroup \
  --server-name vibe-coding \
  --name user_db_001

az postgres db create \
  --resource-group myResourceGroup \
  --server-name vibe-coding \
  --name user_db_002
```

### 2. Get Connection Strings

Format for Azure PostgreSQL:
```
postgresql://username@servername:password@servername.postgres.database.azure.com:5432/database?sslmode=require
```

Example:
```
postgresql://vibeuser@vibe-coding:MyPassword123@vibe-coding.postgres.database.azure.com:5432/user_db_001?sslmode=require
```

### 3. Assign to Users

```bash
python scripts/admin.py --assign-db "user@example.com" "user_db_001" \
  "postgresql://vibeuser@vibe-coding:pass@vibe-coding.postgres.database.azure.com:5432/user_db_001?sslmode=require"
```

## Administrative Operations

### List All Users

```bash
python scripts/admin.py --list-users
```

### View Permissions

```bash
# All permissions
python scripts/admin.py --list-permissions

# Specific user's permissions
python scripts/admin.py --list-permissions "user@example.com"
```

### Revoke Permissions

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 7: Revoke Permission
```

### Deactivate User

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 8: Deactivate User
```

This will:
- Deactivate the user account
- Deactivate all their API keys
- Permissions remain but cannot be used

### Reactivate User

```bash
# Interactive mode
python scripts/admin.py --interactive
# Choose option 9: Activate User
```

## Bulk Setup Script

For setting up multiple users at once, create a script:

```python
# setup_users.py
import asyncio
from scripts.admin import AdminManager

async def setup_all_users():
    admin = AdminManager()
    
    users = [
        {
            "email": "user1@example.com",
            "org": "Team 1",
            "database": "db1",
            "connection": "postgresql://...",
            "permissions": [
                ("db1", "public", "read_write"),
                ("db1", "private", "read_only")
            ]
        },
        # Add more users...
    ]
    
    for user in users:
        # Create user
        await admin.create_user(user["email"], user["org"])
        
        # Generate API key
        api_key = await admin.generate_api_key(
            user["email"], 
            f"API Key for {user['email']}", 
            "prod"
        )
        print(f"API Key for {user['email']}: {api_key}")
        
        # Assign database
        await admin.assign_database(
            user["email"], 
            user["database"], 
            user["connection"]
        )
        
        # Grant permissions
        for db, schema, perm in user["permissions"]:
            await admin.grant_permission(
                user["email"], db, schema, perm
            )

asyncio.run(setup_all_users())
```

## Security Best Practices

1. **API Key Management**
   - Use different API keys for different environments (dev/prod)
   - Set expiration dates for temporary access
   - Rotate API keys regularly
   - Never share API keys

2. **Database Connections**
   - Use strong passwords
   - Always use SSL (sslmode=require)
   - Use read-only database users when possible
   - Separate databases for different customers/projects

3. **Permissions**
   - Follow principle of least privilege
   - Grant read_only unless write access is needed
   - Review permissions regularly
   - Revoke unused permissions

## Troubleshooting

### User Can't Access Database

1. Check user is active:
```bash
python scripts/admin.py --list-users
```

2. Verify database assignment:
```sql
-- Check in master database
SELECT * FROM database_assignments WHERE user_id = (
  SELECT id FROM users WHERE email = 'user@example.com'
);
```

3. Verify permissions:
```bash
python scripts/admin.py --list-permissions "user@example.com"
```

4. Test database connection:
```bash
psql "postgresql://connection_string_here"
```

### API Key Not Working

1. Check if key is active:
```sql
SELECT * FROM api_keys WHERE key_prefix || '_' || LEFT(key_hash, 8) LIKE 'vibe_%';
```

2. Check expiration:
```sql
SELECT name, expires_at, is_active FROM api_keys 
WHERE user_id = (SELECT id FROM users WHERE email = 'user@example.com');
```

3. Generate new key if needed:
```bash
python scripts/admin.py --generate-key "user@example.com" --key-name "New Key"
```

## Example Setup Script

See `scripts/setup_example_users.py` for a complete example of setting up multiple users with different permission levels.

Run it with:
```bash
python scripts/setup_example_users.py
```

## Support

For issues with user management, check:
1. Database connectivity
2. User status (active/inactive)
3. API key validity
4. Permission grants
5. Audit logs for access attempts