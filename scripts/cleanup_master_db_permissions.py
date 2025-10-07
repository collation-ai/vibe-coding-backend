#!/usr/bin/env python3
"""
Cleanup Script: Remove master_db permissions from all users
This script removes any existing master_db access that was inadvertently granted to users
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def cleanup_master_db_permissions():
    """Remove all master_db permissions and database assignments"""

    master_db_url = os.getenv("MASTER_DB_URL")
    if not master_db_url:
        print("❌ MASTER_DB_URL not found in environment")
        return

    conn = await asyncpg.connect(master_db_url)

    try:
        print("=" * 60)
        print("CLEANING UP MASTER_DB PERMISSIONS")
        print("=" * 60)

        # 1. Find all users with master_db schema permissions
        schema_perms = await conn.fetch(
            """
            SELECT sp.id, u.email, sp.schema_name, sp.permission
            FROM schema_permissions sp
            JOIN users u ON sp.user_id = u.id
            WHERE LOWER(sp.database_name) = 'master_db'
            ORDER BY u.email
            """
        )

        if schema_perms:
            print(f"\n📋 Found {len(schema_perms)} schema permissions on master_db:")
            for perm in schema_perms:
                print(
                    f"   - {perm['email']}: {perm['schema_name']} ({perm['permission']})"
                )

            # Delete schema permissions
            deleted_schema = await conn.execute(
                "DELETE FROM schema_permissions WHERE LOWER(database_name) = 'master_db'"
            )
            print(f"✅ Deleted {len(schema_perms)} schema permissions")
        else:
            print("\n✅ No schema permissions found on master_db")

        # 2. Find all users with master_db database assignments
        db_assignments = await conn.fetch(
            """
            SELECT da.id, u.email, da.database_name
            FROM database_assignments da
            JOIN users u ON da.user_id = u.id
            WHERE LOWER(da.database_name) = 'master_db'
            ORDER BY u.email
            """
        )

        if db_assignments:
            print(
                f"\n📋 Found {len(db_assignments)} database assignments for master_db:"
            )
            for assign in db_assignments:
                print(f"   - {assign['email']}: {assign['database_name']}")

            # Delete database assignments
            deleted_assignments = await conn.execute(
                "DELETE FROM database_assignments WHERE LOWER(database_name) = 'master_db'"
            )
            print(f"✅ Deleted {len(db_assignments)} database assignments")
        else:
            print("\n✅ No database assignments found for master_db")

        # 3. Find all PostgreSQL users created on master_db
        pg_users = await conn.fetch(
            """
            SELECT pgu.id, u.email, pgu.pg_username
            FROM pg_database_users pgu
            JOIN users u ON pgu.vibe_user_id = u.id
            WHERE LOWER(pgu.database_name) = 'master_db'
            ORDER BY u.email
            """
        )

        if pg_users:
            print(f"\n📋 Found {len(pg_users)} PostgreSQL users on master_db:")
            for pg_user in pg_users:
                print(f"   - {pg_user['email']}: {pg_user['pg_username']}")

            print(
                "\n⚠️  WARNING: These PostgreSQL users should be manually dropped from master_db"
            )
            print('   Use: DROP USER IF EXISTS "username";')

            # Mark as inactive in our records
            updated_pg_users = await conn.execute(
                "UPDATE pg_database_users SET is_active = false WHERE LOWER(database_name) = 'master_db'"
            )
            print(f"✅ Marked {len(pg_users)} PG users as inactive")
        else:
            print("\n✅ No PostgreSQL users found on master_db")

        # 4. Find all table permissions on master_db
        table_perms = await conn.fetch(
            """
            SELECT tp.id, u.email, tp.schema_name, tp.table_name
            FROM table_permissions tp
            JOIN users u ON tp.vibe_user_id = u.id
            WHERE LOWER(tp.database_name) = 'master_db'
            ORDER BY u.email
            """
        )

        if table_perms:
            print(f"\n📋 Found {len(table_perms)} table permissions on master_db:")
            for perm in table_perms:
                print(
                    f"   - {perm['email']}: {perm['schema_name']}.{perm['table_name']}"
                )

            # Delete table permissions
            deleted_table = await conn.execute(
                "DELETE FROM table_permissions WHERE LOWER(database_name) = 'master_db'"
            )
            print(f"✅ Deleted {len(table_perms)} table permissions")
        else:
            print("\n✅ No table permissions found on master_db")

        # 5. Find all RLS policies on master_db
        rls_policies = await conn.fetch(
            """
            SELECT rp.id, u.email, rp.schema_name, rp.table_name, rp.policy_name
            FROM rls_policies rp
            JOIN users u ON rp.vibe_user_id = u.id
            WHERE LOWER(rp.database_name) = 'master_db' AND rp.is_active = true
            ORDER BY u.email
            """
        )

        if rls_policies:
            print(f"\n📋 Found {len(rls_policies)} RLS policies on master_db:")
            for policy in rls_policies:
                print(
                    f"   - {policy['email']}: {policy['schema_name']}.{policy['table_name']} - {policy['policy_name']}"
                )

            # Mark RLS policies as inactive
            deleted_rls = await conn.execute(
                "UPDATE rls_policies SET is_active = false WHERE LOWER(database_name) = 'master_db'"
            )
            print(f"✅ Marked {len(rls_policies)} RLS policies as inactive")
        else:
            print("\n✅ No RLS policies found on master_db")

        print("\n" + "=" * 60)
        print("✅ CLEANUP COMPLETE!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Schema permissions removed: {len(schema_perms)}")
        print(f"  - Database assignments removed: {len(db_assignments)}")
        print(f"  - PostgreSQL users marked inactive: {len(pg_users)}")
        print(f"  - Table permissions removed: {len(table_perms)}")
        print(f"  - RLS policies marked inactive: {len(rls_policies)}")

        if pg_users:
            print("\n⚠️  MANUAL ACTION REQUIRED:")
            print(
                "   The following PostgreSQL users should be manually dropped from master_db:"
            )
            for pg_user in pg_users:
                print(f"   DROP USER IF EXISTS \"{pg_user['pg_username']}\";")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(cleanup_master_db_permissions())
