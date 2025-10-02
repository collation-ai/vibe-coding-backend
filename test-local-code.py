#!/usr/bin/env python3
"""
Test the LOCAL code (not Azure) with REAL database
This simulates what the gateway will send
"""

import asyncio
import os
from dotenv import load_dotenv

# Load real environment
load_dotenv(".env")

# Import the actual functions
from api.auth.validate import get_permissions
from api.query import execute_raw_query
from schemas.requests import RawQueryRequest


async def test_local_code():
    print("=" * 60)
    print("TESTING LOCAL CODE WITH REAL DATABASE")
    print("=" * 60)

    # Test 1: tanmais permissions (API key owner)
    print("\n1. Testing tanmais permissions (API key owner):")
    try:
        result = await get_permissions(
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ", x_user_id=None
        )
        if hasattr(result, "data"):
            print(f"   ✅ SUCCESS")
            print(f"   Databases: {result.data.get('databases', [])}")
            print(f"   Permissions count: {len(result.data.get('permissions', []))}")
        else:
            print(f"   ❌ ERROR: {result}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 2: freshwaterapiuser via X-User-Id (gateway simulation)
    print("\n2. Testing freshwaterapiuser via X-User-Id (gateway simulation):")
    try:
        result = await get_permissions(
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            x_user_id="d4a34dc6-6699-4183-b068-6c7832291e4b",
        )
        if hasattr(result, "data"):
            print(f"   ✅ SUCCESS")
            print(f"   Databases: {result.data.get('databases', [])}")
            print(f"   Permissions count: {len(result.data.get('permissions', []))}")

            # Show the actual permissions
            for perm in result.data.get("permissions", []):
                print(
                    f"     - {perm['database']}.{perm['schema']}: {perm['permission']}"
                )
        else:
            print(f"   ❌ ERROR: {result}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 3: Query endpoint with tanmais
    print("\n3. Testing query endpoint (tanmais on master_db):")
    try:
        request = RawQueryRequest(
            database="master_db",
            query="SELECT COUNT(*) as user_count FROM users",
            params=[],
        )
        result = await execute_raw_query(
            request=request,
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            x_user_id=None,
        )
        if hasattr(result, "data"):
            print(f"   ✅ SUCCESS")
            print(f"   Result: {result.data.get('rows', [])}")
        else:
            print(f"   ❌ ERROR: {result}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 4: Query endpoint with freshwaterapiuser on their database
    print("\n4. Testing query with freshwaterapiuser on cdb_written_976_poetry:")

    # Test 4a: Simple query on public schema
    print("   4a. Testing simple SELECT 1 query:")
    try:
        request = RawQueryRequest(
            database="cdb_written_976_poetry", query="SELECT 1 as test", params=[]
        )
        result = await execute_raw_query(
            request=request,
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            x_user_id="d4a34dc6-6699-4183-b068-6c7832291e4b",
        )
        if hasattr(result, "data"):
            print(f"      ✅ SUCCESS: {result.data.get('rows', [])}")
        else:
            # It's a JSONResponse error
            if hasattr(result, "body"):
                import json

                error_body = json.loads(result.body)
                print(
                    f"      ❌ ERROR: {error_body.get('error', {}).get('message', 'Unknown error')}"
                )
            else:
                print(f"      ❌ ERROR: {result}")
    except Exception as e:
        print(f"      ❌ ERROR: {e}")

    # Test 4b: Query on information_schema
    print("   4b. Testing information_schema query:")
    try:
        request = RawQueryRequest(
            database="cdb_written_976_poetry",
            query="SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5",
            params=[],
        )
        result = await execute_raw_query(
            request=request,
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            x_user_id="d4a34dc6-6699-4183-b068-6c7832291e4b",
        )
        if hasattr(result, "data"):
            print(f"      ✅ SUCCESS")
            rows = result.data.get("rows", [])
            print(f"      Tables found: {len(rows)}")
            for row in rows[:3]:
                print(f"        - {row.get('table_name', 'unknown')}")
        else:
            # It's a JSONResponse error
            if hasattr(result, "body"):
                import json

                error_body = json.loads(result.body)
                print(
                    f"      ❌ ERROR: {error_body.get('error', {}).get('message', 'Unknown error')}"
                )
            else:
                print(f"      ❌ ERROR: {result}")
    except Exception as e:
        print(f"      ❌ ERROR: {e}")

    # Test 5: Try query on master_db with freshwaterapiuser
    print("\n5. Testing freshwaterapiuser query on master_db (has read_write):")
    try:
        request = RawQueryRequest(
            database="master_db",
            query="SELECT COUNT(*) as perm_count FROM schema_permissions WHERE user_id = 'd4a34dc6-6699-4183-b068-6c7832291e4b'::uuid",
            params=[],
        )
        result = await execute_raw_query(
            request=request,
            x_api_key="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            x_user_id="d4a34dc6-6699-4183-b068-6c7832291e4b",
        )
        if hasattr(result, "data"):
            print(f"   ✅ SUCCESS")
            print(f"   Result: {result.data.get('rows', [])}")
        else:
            # It's a JSONResponse error
            if hasattr(result, "body"):
                import json

                error_body = json.loads(result.body)
                print(
                    f"   ❌ ERROR: {error_body.get('error', {}).get('message', 'Unknown error')}"
                )
            else:
                print(f"   ❌ ERROR: {result}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 60)
    print("LOCAL TESTING COMPLETE")
    print("If all show ✅, the code is ready to deploy to Azure")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_local_code())
