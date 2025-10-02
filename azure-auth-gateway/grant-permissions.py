#!/usr/bin/env python3
"""
Quick script to grant schema permissions to users
Usage: python3 grant-permissions.py <username> <database> <schema> <permission>

Example:
  python3 grant-permissions.py john_doe master_db public read_write
  python3 grant-permissions.py jane_smith analytics information_schema read_only
"""

import asyncpg
import asyncio
import uuid
import sys
from datetime import datetime

MASTER_DB_URL = "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"


async def grant_permission(username, database_name, schema_name, permission):
    """Grant schema permission to a user"""

    conn = await asyncpg.connect(MASTER_DB_URL)

    try:
        # Get user ID
        user_id = await conn.fetchval(
            """
            SELECT id FROM users WHERE username = $1
        """,
            username,
        )

        if not user_id:
            print(f"❌ User '{username}' not found")
            return False

        # Check if database is assigned
        db_assigned = await conn.fetchval(
            """
            SELECT database_name FROM database_assignments 
            WHERE user_id = $1 AND database_name = $2 AND is_active = true
        """,
            user_id,
            database_name,
        )

        if not db_assigned:
            print(f"❌ User doesn't have access to database '{database_name}'")
            print(f"   First assign the database to the user")
            return False

        # Check existing permission
        existing = await conn.fetchrow(
            """
            SELECT permission FROM schema_permissions
            WHERE user_id = $1 AND database_name = $2 AND schema_name = $3
        """,
            user_id,
            database_name,
            schema_name,
        )

        if existing:
            if existing["permission"] == permission:
                print(
                    f"ℹ️  User already has {permission} on {database_name}.{schema_name}"
                )
                return True

            # Update permission
            await conn.execute(
                """
                UPDATE schema_permissions
                SET permission = $1, updated_at = $2
                WHERE user_id = $3 AND database_name = $4 AND schema_name = $5
            """,
                permission,
                datetime.utcnow(),
                user_id,
                database_name,
                schema_name,
            )

            print(f"✓ Updated: {username} permission on {database_name}.{schema_name}")
            print(f"  Changed from '{existing['permission']}' to '{permission}'")
        else:
            # Create new permission
            await conn.execute(
                """
                INSERT INTO schema_permissions (id, user_id, database_name, schema_name, permission, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid.uuid4(),
                user_id,
                database_name,
                schema_name,
                permission,
                datetime.utcnow(),
                datetime.utcnow(),
            )

            print(
                f"✓ Granted: {username} now has {permission} on {database_name}.{schema_name}"
            )

        # Show all permissions for this database
        print(f"\nCurrent permissions for {username} on {database_name}:")
        permissions = await conn.fetch(
            """
            SELECT schema_name, permission
            FROM schema_permissions
            WHERE user_id = $1 AND database_name = $2
            ORDER BY schema_name
        """,
            user_id,
            database_name,
        )

        for perm in permissions:
            icon = "✏️" if perm["permission"] == "read_write" else "👁️"
            print(f"  {icon} {perm['schema_name']}: {perm['permission']}")

        return True

    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) == 5:
        # Command line usage
        _, username, database, schema, permission = sys.argv

        if permission not in ["read_only", "read_write"]:
            print("❌ Permission must be 'read_only' or 'read_write'")
            sys.exit(1)

        asyncio.run(grant_permission(username, database, schema, permission))

    else:
        # Interactive mode
        print("=== Schema Permission Manager ===\n")
        username = input("Username: ")
        database = input("Database name: ")
        schema = input("Schema name: ")
        permission = input("Permission (read_only/read_write): ").lower()

        if permission not in ["read_only", "read_write"]:
            print("❌ Invalid permission type")
            sys.exit(1)

        asyncio.run(grant_permission(username, database, schema, permission))
