import asyncpg
import asyncio


async def check_user_permissions():
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )

    # Check user
    user = await conn.fetchrow(
        """
        SELECT id, username, email FROM users WHERE username = 'freshwaterapiuser'
    """
    )

    if user:
        print(f"User found: {user['username']} (ID: {user['id']})")
        print(f"Email: {user['email']}")
        print()

        # Check database assignments
        print("Database Assignments:")
        db_assignments = await conn.fetch(
            """
            SELECT database_name, is_active, created_at
            FROM database_assignments
            WHERE user_id = $1
            ORDER BY database_name
        """,
            user["id"],
        )

        for db in db_assignments:
            status = "✓" if db["is_active"] else "✗"
            print(f"  {status} {db['database_name']} (added: {db['created_at']})")

        print("\nSchema Permissions:")
        # Check schema permissions
        permissions = await conn.fetch(
            """
            SELECT database_name, schema_name, permission, created_at
            FROM schema_permissions
            WHERE user_id = $1
            ORDER BY database_name, schema_name
        """,
            user["id"],
        )

        for perm in permissions:
            icon = "✏️" if perm["permission"] == "read_write" else "👁️"
            print(
                f"  {icon} {perm['database_name']}.{perm['schema_name']}: {perm['permission']}"
            )
    else:
        print("User 'freshwaterapiuser' not found")

    await conn.close()


asyncio.run(check_user_permissions())
