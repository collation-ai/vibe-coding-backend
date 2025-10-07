#!/usr/bin/env python3
"""
Create a new admin API key
"""
import asyncio
import sys
import os

# Set environment variables from .env file if not already set
if not os.getenv('ENCRYPTION_KEY'):
    os.environ['ENCRYPTION_KEY'] = 'Q83SKjnvUTBNCD8yEO/AOUd7xh6QWFEUqYKaq1wrtrs='
    os.environ['API_KEY_SALT'] = '7GcyvOMC7BH8k4IZ76GYnub7IOzcYU4b9P+VimRLi7E='
    os.environ['MASTER_DB_URL'] = 'postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require'

sys.path.insert(0, '.')

from lib.auth import auth_manager
from lib.database import db_manager


async def create_admin_key():
    """Create a new API key for the admin user"""

    # Connect to database
    pool = await db_manager.get_master_pool()

    async with pool.acquire() as conn:
        # Check if tanmais user exists
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "tanmais@example.com"
        )

        if not user:
            # Create the admin user if doesn't exist
            print("Admin user not found. Creating...")
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, username, password_hash, organization, is_active)
                VALUES ($1, $2, $3, $4, true)
                RETURNING id
                """,
                "tanmais@example.com",
                "tanmais",
                "$2b$12$dummyhashfornopasswordlogin123456",  # Dummy hash
                "Vibe Coding Admin"
            )
            print(f"✅ Created admin user: {user_id}")
        else:
            user_id = user['id']
            print(f"✅ Found existing admin user: {user['email']}")

        # Generate new API key
        print("\nGenerating new API key...")
        api_key = await auth_manager.create_api_key(
            user_id=str(user_id),
            name="Admin Dashboard Key",
            environment="prod",
            expires_in_days=None  # Never expires
        )

        print("\n" + "="*60)
        print("🔑 NEW ADMIN API KEY GENERATED!")
        print("="*60)
        print(f"\n{api_key}\n")
        print("="*60)
        print("\n⚠️  IMPORTANT: Save this key securely!")
        print("   This is the only time you'll see it.")
        print("\n💡 Use this key to login to the admin dashboard at:")
        print("   http://localhost:8000/admin")
        print("\n")


if __name__ == "__main__":
    asyncio.run(create_admin_key())
