#!/usr/bin/env python3
"""
Admin script for managing users, databases, and permissions
"""

import asyncio
import asyncpg
import os
import sys
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import getpass

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.auth import auth_manager

# Load environment variables
load_dotenv()


class AdminManager:
    def __init__(self):
        self.master_db_url = os.getenv("MASTER_DB_URL")
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.master_db_url:
            print("❌ MASTER_DB_URL not found in .env")
            sys.exit(1)
        if not self.encryption_key:
            print("❌ ENCRYPTION_KEY not found in .env")
            sys.exit(1)
        self.fernet = Fernet(self.encryption_key.encode())

    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.master_db_url)

    async def create_user(self, email: str, organization: Optional[str] = None):
        """Create a new user"""
        conn = await self.get_connection()
        try:
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, organization)
                VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE SET organization = $2
                RETURNING id
                """,
                email,
                organization,
            )
            print(f"✅ User created/updated: {email}")
            print(f"   User ID: {user_id}")
            return user_id
        finally:
            await conn.close()

    async def generate_api_key(
        self,
        email: str,
        key_name: str,
        environment: str = "prod",
        expires_days: Optional[int] = None,
    ):
        """Generate an API key for a user"""
        conn = await self.get_connection()
        try:
            # Get user ID
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email
            )
            if not user_id:
                print(f"❌ User not found: {email}")
                return None

            # Generate API key
            api_key, key_hash = auth_manager.generate_api_key(environment)

            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)

            # Store in database
            await conn.execute(
                """
                INSERT INTO api_keys (user_id, key_hash, key_prefix, name, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                key_hash,
                f"vibe_{environment}",
                key_name,
                expires_at,
            )

            print(f"✅ API Key generated for {email}")
            print(f"   Key Name: {key_name}")
            print(f"   API Key: {api_key}")
            print(f"   Expires: {expires_at or 'Never'}")
            print("\n⚠️  IMPORTANT: Save this API key - it cannot be retrieved again!")
            return api_key
        finally:
            await conn.close()

    async def assign_database(
        self, email: str, database_name: str, connection_string: str
    ):
        """Assign a database to a user"""
        conn = await self.get_connection()
        try:
            # Get user ID
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email
            )
            if not user_id:
                print(f"❌ User not found: {email}")
                return False

            # Encrypt connection string
            encrypted_url = self.fernet.encrypt(connection_string.encode()).decode()

            # Store assignment
            await conn.execute(
                """
                INSERT INTO database_assignments (user_id, database_name, connection_string_encrypted)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, database_name)
                DO UPDATE SET connection_string_encrypted = $3
                """,
                user_id,
                database_name,
                encrypted_url,
            )

            print(f"✅ Database assigned to {email}")
            print(f"   Database: {database_name}")
            return True
        finally:
            await conn.close()

    async def grant_permission(
        self, email: str, database_name: str, schema_name: str, permission: str
    ):
        """Grant permission on a schema to a user"""
        conn = await self.get_connection()
        try:
            # Get user ID
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email
            )
            if not user_id:
                print(f"❌ User not found: {email}")
                return False

            # Validate permission
            if permission not in ["read_only", "read_write"]:
                print(f"❌ Invalid permission: {permission}")
                print("   Use: read_only or read_write")
                return False

            # Grant permission
            await conn.execute(
                """
                INSERT INTO schema_permissions (user_id, database_name, schema_name, permission)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, database_name, schema_name)
                DO UPDATE SET permission = $4, updated_at = NOW()
                """,
                user_id,
                database_name,
                schema_name,
                permission,
            )

            print(f"✅ Permission granted to {email}")
            print(f"   Database: {database_name}")
            print(f"   Schema: {schema_name}")
            print(f"   Permission: {permission}")
            return True
        finally:
            await conn.close()

    async def list_users(self):
        """List all users"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT u.id, u.email, u.organization, u.created_at, u.is_active,
                       COUNT(DISTINCT ak.id) as api_keys_count,
                       COUNT(DISTINCT da.id) as databases_count
                FROM users u
                LEFT JOIN api_keys ak ON u.id = ak.user_id AND ak.is_active = true
                LEFT JOIN database_assignments da ON u.id = da.user_id
                GROUP BY u.id
                ORDER BY u.created_at DESC
                """
            )

            print("\n" + "=" * 80)
            print("USERS")
            print("=" * 80)

            for row in rows:
                status = "✅ Active" if row["is_active"] else "❌ Inactive"
                print(f"\n📧 {row['email']} ({status})")
                print(f"   Organization: {row['organization'] or 'N/A'}")
                print(f"   User ID: {row['id']}")
                print(f"   API Keys: {row['api_keys_count']}")
                print(f"   Databases: {row['databases_count']}")
                print(f"   Created: {row['created_at']}")

            print("\n" + "=" * 80)
            print(f"Total users: {len(rows)}")
            return rows
        finally:
            await conn.close()

    async def list_permissions(self, email: Optional[str] = None):
        """List permissions for a user or all users"""
        conn = await self.get_connection()
        try:
            if email:
                query = """
                    SELECT u.email, sp.database_name, sp.schema_name, sp.permission, sp.created_at
                    FROM schema_permissions sp
                    JOIN users u ON sp.user_id = u.id
                    WHERE u.email = $1
                    ORDER BY sp.database_name, sp.schema_name
                """
                rows = await conn.fetch(query, email)
            else:
                query = """
                    SELECT u.email, sp.database_name, sp.schema_name, sp.permission, sp.created_at
                    FROM schema_permissions sp
                    JOIN users u ON sp.user_id = u.id
                    ORDER BY u.email, sp.database_name, sp.schema_name
                """
                rows = await conn.fetch(query)

            print("\n" + "=" * 80)
            print(f"PERMISSIONS" + (f" for {email}" if email else ""))
            print("=" * 80)

            current_user = None
            for row in rows:
                if row["email"] != current_user:
                    current_user = row["email"]
                    print(f"\n📧 {current_user}")

                perm_icon = "✏️" if row["permission"] == "read_write" else "👁️"
                print(
                    f"   {perm_icon} {row['database_name']}.{row['schema_name']} ({row['permission']})"
                )

            if not rows:
                print("No permissions found")

            print("\n" + "=" * 80)
            return rows
        finally:
            await conn.close()

    async def revoke_permission(self, email: str, database_name: str, schema_name: str):
        """Revoke permission on a schema from a user"""
        conn = await self.get_connection()
        try:
            # Get user ID
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email
            )
            if not user_id:
                print(f"❌ User not found: {email}")
                return False

            # Revoke permission
            result = await conn.execute(
                """
                DELETE FROM schema_permissions
                WHERE user_id = $1 AND database_name = $2 AND schema_name = $3
                """,
                user_id,
                database_name,
                schema_name,
            )

            if "DELETE 1" in result:
                print(f"✅ Permission revoked from {email}")
                print(f"   Database: {database_name}")
                print(f"   Schema: {schema_name}")
                return True
            else:
                print("❌ Permission not found")
                return False
        finally:
            await conn.close()

    async def deactivate_user(self, email: str):
        """Deactivate a user"""
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                "UPDATE users SET is_active = false WHERE email = $1", email
            )

            if "UPDATE 1" in result:
                # Also deactivate their API keys
                await conn.execute(
                    """
                    UPDATE api_keys SET is_active = false
                    WHERE user_id = (SELECT id FROM users WHERE email = $1)
                    """,
                    email,
                )
                print(f"✅ User deactivated: {email}")
                return True
            else:
                print(f"❌ User not found: {email}")
                return False
        finally:
            await conn.close()

    async def activate_user(self, email: str):
        """Activate a user"""
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                "UPDATE users SET is_active = true WHERE email = $1", email
            )

            if "UPDATE 1" in result:
                print(f"✅ User activated: {email}")
                return True
            else:
                print(f"❌ User not found: {email}")
                return False
        finally:
            await conn.close()


async def interactive_menu():
    """Interactive menu for admin operations"""
    admin = AdminManager()

    while True:
        print("\n" + "=" * 50)
        print("VIBE CODING BACKEND - ADMIN CONSOLE")
        print("=" * 50)
        print("\n1. Create User")
        print("2. Generate API Key")
        print("3. Assign Database")
        print("4. Grant Permission")
        print("5. List Users")
        print("6. List Permissions")
        print("7. Revoke Permission")
        print("8. Deactivate User")
        print("9. Activate User")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        try:
            if choice == "1":
                email = input("Email: ").strip()
                org = input("Organization (optional): ").strip() or None
                await admin.create_user(email, org)

            elif choice == "2":
                email = input("User email: ").strip()
                name = input("Key name (e.g., 'Development Key'): ").strip()
                env = input("Environment (dev/prod) [prod]: ").strip() or "prod"
                expires = input(
                    "Expires in days (leave empty for no expiration): "
                ).strip()
                expires_days = int(expires) if expires else None
                await admin.generate_api_key(email, name, env, expires_days)

            elif choice == "3":
                email = input("User email: ").strip()
                db_name = input("Database name (e.g., 'user_db_001'): ").strip()
                print("Enter PostgreSQL connection string:")
                print(
                    "Format: postgresql://user:pass@host:port/database?sslmode=require"
                )
                conn_str = input("Connection string: ").strip()
                await admin.assign_database(email, db_name, conn_str)

            elif choice == "4":
                email = input("User email: ").strip()
                db_name = input("Database name: ").strip()
                schema = input("Schema name (e.g., 'public'): ").strip()
                perm = input("Permission (read_only/read_write): ").strip()
                await admin.grant_permission(email, db_name, schema, perm)

            elif choice == "5":
                await admin.list_users()
                input("\nPress Enter to continue...")

            elif choice == "6":
                email = input("User email (leave empty for all): ").strip() or None
                await admin.list_permissions(email)
                input("\nPress Enter to continue...")

            elif choice == "7":
                email = input("User email: ").strip()
                db_name = input("Database name: ").strip()
                schema = input("Schema name: ").strip()
                await admin.revoke_permission(email, db_name, schema)

            elif choice == "8":
                email = input("User email to deactivate: ").strip()
                confirm = input(
                    f"Are you sure you want to deactivate {email}? (yes/no): "
                ).strip()
                if confirm.lower() == "yes":
                    await admin.deactivate_user(email)

            elif choice == "9":
                email = input("User email to activate: ").strip()
                await admin.activate_user(email)

            elif choice == "0":
                print("\nExiting...")
                break

            else:
                print("❌ Invalid option")

        except Exception as e:
            print(f"❌ Error: {e}")
            input("\nPress Enter to continue...")


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Admin tools for Vibe Coding Backend")
    parser.add_argument("--create-user", metavar="EMAIL", help="Create a new user")
    parser.add_argument("--org", help="Organization for new user")
    parser.add_argument(
        "--generate-key", metavar="EMAIL", help="Generate API key for user"
    )
    parser.add_argument("--key-name", default="API Key", help="Name for the API key")
    parser.add_argument(
        "--env", default="prod", choices=["dev", "prod"], help="Environment"
    )
    parser.add_argument(
        "--assign-db",
        nargs=3,
        metavar=("EMAIL", "DB_NAME", "CONN_STRING"),
        help="Assign database to user",
    )
    parser.add_argument(
        "--grant",
        nargs=4,
        metavar=("EMAIL", "DB", "SCHEMA", "PERM"),
        help="Grant permission (read_only/read_write)",
    )
    parser.add_argument("--list-users", action="store_true", help="List all users")
    parser.add_argument(
        "--list-permissions",
        metavar="EMAIL",
        nargs="?",
        const="",
        help="List permissions",
    )
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()
    admin = AdminManager()

    if args.interactive or len(sys.argv) == 1:
        await interactive_menu()
    elif args.create_user:
        await admin.create_user(args.create_user, args.org)
    elif args.generate_key:
        await admin.generate_api_key(args.generate_key, args.key_name, args.env)
    elif args.assign_db:
        email, db_name, conn_str = args.assign_db
        await admin.assign_database(email, db_name, conn_str)
    elif args.grant:
        email, db, schema, perm = args.grant
        await admin.grant_permission(email, db, schema, perm)
    elif args.list_users:
        await admin.list_users()
    elif args.list_permissions is not None:
        email = args.list_permissions if args.list_permissions else None
        await admin.list_permissions(email)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
