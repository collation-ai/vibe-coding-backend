#!/usr/bin/env python3
"""
Simple test for the permissions endpoint using asyncio correctly
"""

import asyncio
import os
import sys

# Set up environment
os.environ["MASTER_DB_URL"] = os.environ.get("MASTER_DB_URL", "")
os.environ["ENCRYPTION_KEY"] = os.environ.get("ENCRYPTION_KEY", "")
os.environ["API_KEY_SALT"] = os.environ.get("API_KEY_SALT", "")

from lib.auth import auth_manager
from lib.permissions import permission_manager


async def test_permissions():
    print("=" * 60)
    print("TESTING PERMISSION RETRIEVAL")
    print("=" * 60)

    # Test 1: Validate API key (tanmais)
    print("\n1. Testing tanmais's API key:")
    user_info = await auth_manager.validate_api_key(
        "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
    )
    if user_info:
        print(f"   ✅ API key valid for user: {user_info['email']}")
        print(f"   User ID: {user_info['user_id']}")

        # Get tanmais's permissions
        perms = await permission_manager.get_user_permissions(user_info["user_id"])
        dbs = await permission_manager.get_accessible_databases(user_info["user_id"])
        print(f"   Permissions: {len(perms)} found")
        print(f"   Databases: {dbs}")
    else:
        print("   ❌ Invalid API key")

    # Test 2: Get freshwaterapiuser's permissions using their ID
    print("\n2. Testing freshwaterapiuser's permissions:")
    fresh_user_id = "d4a34dc6-6699-4183-b068-6c7832291e4b"
    print(f"   User ID: {fresh_user_id}")

    try:
        perms = await permission_manager.get_user_permissions(fresh_user_id)
        dbs = await permission_manager.get_accessible_databases(fresh_user_id)
        print(f"   ✅ Permissions: {len(perms)} found")
        print(f"   Databases: {dbs}")

        # Show details
        for perm in perms:
            print(f"      - {perm['database']}.{perm['schema']}: {perm['permission']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_permissions())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
