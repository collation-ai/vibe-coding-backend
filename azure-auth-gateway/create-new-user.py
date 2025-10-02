#!/usr/bin/env python3
"""
Script to create a new user with API access for the Vibe Coding Backend

This script:
1. Creates a user account with login credentials
2. Generates an API key for backend access
3. Assigns database connections (can be multiple)
4. Sets up schema permissions
"""

import asyncpg
import asyncio
import bcrypt
import hashlib
import secrets
import uuid
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import sys

# Configuration
MASTER_DB_URL = "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
ENCRYPTION_KEY = "Q83SKjnvUTBNCD8yEO/AOUd7xh6QWFEUqYKaq1wrtrs="  # From Azure settings
API_KEY_SALT = "7GcyvOMC7BH8k4IZ76GYnub7IOzcYU4b9P+VimRLi7E="  # From Azure settings

async def create_user(username, email, password, organization):
    """Create a new user with login credentials and API access"""
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    fernet = Fernet(ENCRYPTION_KEY.encode())
    
    try:
        # 1. Create the user account
        print(f"\n1. Creating user account for {username}...")
        
        # Hash the password for login authentication
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert user
        user_id = await conn.fetchval("""
            INSERT INTO users (id, username, email, password_hash, organization, created_at, updated_at, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """, 
            uuid.uuid4(),
            username,
            email,
            password_hash,
            organization,
            datetime.utcnow(),
            datetime.utcnow(),
            True
        )
        
        print(f"✓ User created with ID: {user_id}")
        
        # 2. Generate API key for backend access
        print(f"\n2. Generating API key...")
        
        # Generate a secure random API key
        api_key = f"vibe_prod_{secrets.token_urlsafe(32)}"
        
        # Hash the API key with salt for storage
        salted_key = api_key + API_KEY_SALT
        key_hash = hashlib.sha256(salted_key.encode()).hexdigest()
        
        # Store the API key
        api_key_id = await conn.fetchval("""
            INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, created_at, expires_at, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            uuid.uuid4(),
            user_id,
            key_hash,
            api_key[:14],  # Store prefix for identification
            f"Primary API key for {username}",
            datetime.utcnow(),
            datetime.utcnow() + timedelta(days=365),  # 1 year expiry
            True
        )
        
        print(f"✓ API key generated")
        print(f"  API Key ID: {api_key_id}")
        print(f"  API Key (SAVE THIS): {api_key}")
        
        # 3. Assign database connections
        print(f"\n3. Assigning database access...")
        
        # Example: Assign master_db access (you can add multiple databases)
        databases_to_assign = [
            {
                "name": "master_db",
                "connection_string": MASTER_DB_URL,
                "description": "Master database with user management"
            },
            # Add more databases here if needed:
            # {
            #     "name": "analytics_db",
            #     "connection_string": "postgresql://user:pass@host/analytics_db?sslmode=require",
            #     "description": "Analytics database"
            # },
        ]
        
        for db in databases_to_assign:
            # Encrypt the connection string
            encrypted_conn = fernet.encrypt(db["connection_string"].encode()).decode()
            
            # Create database assignment
            await conn.execute("""
                INSERT INTO database_assignments (id, user_id, database_name, connection_string_encrypted, created_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                uuid.uuid4(),
                user_id,
                db["name"],
                encrypted_conn,
                datetime.utcnow(),
                True
            )
            
            print(f"  ✓ Assigned database: {db['name']} - {db['description']}")
        
        # 4. Set up schema permissions
        print(f"\n4. Setting up schema permissions...")
        
        # Example permissions (customize as needed)
        permissions_to_grant = [
            {"database": "master_db", "schema": "public", "permission": "read_write"},
            {"database": "master_db", "schema": "information_schema", "permission": "read_only"},
            # Add more schema permissions as needed
        ]
        
        for perm in permissions_to_grant:
            await conn.execute("""
                INSERT INTO schema_permissions (id, user_id, database_name, schema_name, permission, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid.uuid4(),
                user_id,
                perm["database"],
                perm["schema"],
                perm["permission"],
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            print(f"  ✓ Granted {perm['permission']} on {perm['database']}.{perm['schema']}")
        
        print(f"\n✅ User setup complete!")
        print(f"\n=== IMPORTANT: Save these credentials ===")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"API Key: {api_key}")
        print(f"Login URL: https://vibe-auth-gateway.azurewebsites.net/api/auth/login")
        print(f"=====================================\n")
        
        return user_id, api_key
        
    finally:
        await conn.close()


async def add_database_to_existing_user(username, database_name, connection_string):
    """Add additional database access to an existing user"""
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    fernet = Fernet(ENCRYPTION_KEY.encode())
    
    try:
        # Get user ID
        user_id = await conn.fetchval("""
            SELECT id FROM users WHERE username = $1
        """, username)
        
        if not user_id:
            print(f"❌ User '{username}' not found")
            return
        
        # Check if assignment already exists
        existing = await conn.fetchval("""
            SELECT database_name FROM database_assignments 
            WHERE user_id = $1 AND database_name = $2
        """, user_id, database_name)
        
        if existing:
            print(f"⚠️  Database '{database_name}' already assigned to user")
            return
        
        # Encrypt and store the connection
        encrypted_conn = fernet.encrypt(connection_string.encode()).decode()
        
        await conn.execute("""
            INSERT INTO database_assignments (id, user_id, database_name, connection_string_encrypted, created_at, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            uuid.uuid4(),
            user_id,
            database_name,
            encrypted_conn,
            datetime.utcnow(),
            True
        )
        
        print(f"✓ Added database '{database_name}' to user '{username}'")
        
    finally:
        await conn.close()


async def grant_schema_permission(username, database_name, schema_name, permission):
    """Grant read_only or read_write permission on a schema to a user"""
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    
    try:
        # Get user ID
        user_id = await conn.fetchval("""
            SELECT id FROM users WHERE username = $1
        """, username)
        
        if not user_id:
            print(f"❌ User '{username}' not found")
            return
        
        # Check if database is assigned to user
        db_assigned = await conn.fetchval("""
            SELECT database_name FROM database_assignments 
            WHERE user_id = $1 AND database_name = $2 AND is_active = true
        """, user_id, database_name)
        
        if not db_assigned:
            print(f"❌ User doesn't have access to database '{database_name}'")
            print(f"   First assign the database using option 2")
            return
        
        # Check if permission already exists
        existing = await conn.fetchrow("""
            SELECT permission FROM schema_permissions
            WHERE user_id = $1 AND database_name = $2 AND schema_name = $3
        """, user_id, database_name, schema_name)
        
        if existing:
            # Update existing permission
            await conn.execute("""
                UPDATE schema_permissions
                SET permission = $1, updated_at = $2
                WHERE user_id = $3 AND database_name = $4 AND schema_name = $5
            """, permission, datetime.utcnow(), user_id, database_name, schema_name)
            
            print(f"✓ Updated permission from '{existing['permission']}' to '{permission}'")
        else:
            # Create new permission
            await conn.execute("""
                INSERT INTO schema_permissions (id, user_id, database_name, schema_name, permission, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid.uuid4(),
                user_id,
                database_name,
                schema_name,
                permission,
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            print(f"✓ Granted {permission} permission on {database_name}.{schema_name} to {username}")
        
    finally:
        await conn.close()


async def list_user_permissions(username):
    """List all schema permissions for a user"""
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    
    try:
        rows = await conn.fetch("""
            SELECT sp.database_name, sp.schema_name, sp.permission, sp.updated_at
            FROM users u
            JOIN schema_permissions sp ON u.id = sp.user_id
            WHERE u.username = $1
            ORDER BY sp.database_name, sp.schema_name
        """, username)
        
        if not rows:
            print(f"No permissions found for user '{username}'")
            return
        
        print(f"\nSchema permissions for user '{username}':")
        print("-" * 70)
        current_db = None
        for row in rows:
            if current_db != row['database_name']:
                current_db = row['database_name']
                print(f"\n📁 Database: {current_db}")
            
            icon = "✏️" if row['permission'] == 'read_write' else "👁️"
            print(f"   {icon} {row['schema_name']}: {row['permission']}")
            
    finally:
        await conn.close()


async def list_user_databases(username):
    """List all databases assigned to a user"""
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    
    try:
        rows = await conn.fetch("""
            SELECT da.database_name, da.created_at, da.is_active,
                   COUNT(sp.id) as permission_count
            FROM users u
            JOIN database_assignments da ON u.id = da.user_id
            LEFT JOIN schema_permissions sp ON u.id = sp.user_id AND da.database_name = sp.database_name
            WHERE u.username = $1
            GROUP BY da.database_name, da.created_at, da.is_active
            ORDER BY da.created_at DESC
        """, username)
        
        if not rows:
            print(f"No databases found for user '{username}'")
            return
        
        print(f"\nDatabases for user '{username}':")
        print("-" * 60)
        for row in rows:
            status = "Active" if row['is_active'] else "Inactive"
            print(f"Database: {row['database_name']}")
            print(f"  Status: {status}")
            print(f"  Permissions: {row['permission_count']} schema(s)")
            print(f"  Added: {row['created_at']}")
            print()
            
    finally:
        await conn.close()


# Example usage
if __name__ == "__main__":
    print("=== Vibe Coding Backend - User & Permission Management ===\n")
    print("USER MANAGEMENT:")
    print("1. Create new user with API access")
    print("2. Add database to existing user")
    print("3. List user's databases")
    print("\nPERMISSION MANAGEMENT:")
    print("4. Grant schema permission to user")
    print("5. List user's schema permissions")
    print("\n6. Exit")
    
    choice = input("\nSelect option (1-6): ")
    
    if choice == "1":
        # Create new user
        username = input("Username: ")
        email = input("Email: ")
        password = input("Password: ")
        organization = input("Organization: ")
        
        asyncio.run(create_user(username, email, password, organization))
        
    elif choice == "2":
        # Add database to existing user
        username = input("Username: ")
        database_name = input("Database name: ")
        connection_string = input("Connection string (postgresql://...): ")
        
        asyncio.run(add_database_to_existing_user(username, database_name, connection_string))
        
    elif choice == "3":
        # List user databases
        username = input("Username: ")
        asyncio.run(list_user_databases(username))
        
    elif choice == "4":
        # Grant schema permission
        username = input("Username: ")
        database_name = input("Database name: ")
        schema_name = input("Schema name (e.g., 'public', 'information_schema'): ")
        permission = input("Permission type (read_only or read_write): ").lower()
        
        if permission not in ['read_only', 'read_write']:
            print("❌ Invalid permission. Must be 'read_only' or 'read_write'")
        else:
            asyncio.run(grant_schema_permission(username, database_name, schema_name, permission))
        
    elif choice == "5":
        # List user permissions
        username = input("Username: ")
        asyncio.run(list_user_permissions(username))
        
    else:
        print("Exiting...")