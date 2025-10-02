import asyncpg
import asyncio
import sys


async def show_permissions(username):
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )

    # Get user info
    user = await conn.fetchrow(
        """
        SELECT id, username, email, organization
        FROM users WHERE username = $1
    """,
        username,
    )

    if not user:
        print(f"User '{username}' not found")
        await conn.close()
        return

    print(f"=== Permissions for {user['username']} ===")
    print(f"Email: {user['email']}")
    print(f"Organization: {user['organization']}")
    print()

    # Get database assignments
    print("📁 Database Access:")
    db_assignments = await conn.fetch(
        """
        SELECT database_name, is_active
        FROM database_assignments
        WHERE user_id = $1 AND is_active = true
        ORDER BY database_name
    """,
        user["id"],
    )

    if not db_assignments:
        print("  No databases assigned")
    else:
        for db in db_assignments:
            print(f"  ✓ {db['database_name']}")

    print("\n🔐 Schema Permissions:")
    # Get schema permissions
    permissions = await conn.fetch(
        """
        SELECT database_name, schema_name, permission
        FROM schema_permissions
        WHERE user_id = $1
        ORDER BY database_name, schema_name
    """,
        user["id"],
    )

    if not permissions:
        print("  No schema permissions granted")
    else:
        current_db = None
        for perm in permissions:
            if current_db != perm["database_name"]:
                current_db = perm["database_name"]
                print(f"\n  Database: {current_db}")

            icon = "✏️" if perm["permission"] == "read_write" else "👁️"
            print(f"    {icon} {perm['schema_name']}: {perm['permission']}")

    print("\n" + "=" * 40)
    print("This is what the API SHOULD return for this user")
    print("when called with their API key or session.")

    await conn.close()


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "freshwaterapiuser"
    asyncio.run(show_permissions(username))
