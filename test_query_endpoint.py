#!/usr/bin/env python3
"""
Test the /api/query endpoint after fixing asyncio import
"""

import httpx
import json

BASE_URL = "http://localhost:8000"
API_KEY = "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
DATABASE = "minerva_pear"


def test_simple_select():
    """Test simple SELECT query"""
    print("\n" + "=" * 60)
    print("📊 Testing Simple SELECT Query")
    print("=" * 60)

    data = {
        "database": DATABASE,
        "query": "SELECT COUNT(*) as total FROM collation_storage.users",
        "params": [],
        "read_only": True,
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Query successful!")
            print(f"   Total users: {result['data']['rows'][0]['total']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_parameterized_query():
    """Test query with parameters"""
    print("\n" + "=" * 60)
    print("🔍 Testing Parameterized Query")
    print("=" * 60)

    data = {
        "database": DATABASE,
        "query": "SELECT id, name FROM collation_storage.users WHERE name LIKE $1 ORDER BY id DESC LIMIT $2",
        "params": ["%Test%", 5],
        "read_only": True,
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            row_count = result["data"]["row_count"]
            print(f"✅ Parameterized query successful! Found {row_count} matching rows")
            if row_count > 0:
                print(f"   First match: {result['data']['rows'][0]}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_aggregate_query():
    """Test aggregate functions"""
    print("\n" + "=" * 60)
    print("📈 Testing Aggregate Query")
    print("=" * 60)

    data = {
        "database": DATABASE,
        "query": """
            SELECT
                COUNT(*) as total_users,
                COUNT(DISTINCT name) as unique_names,
                MAX(id) as max_id,
                MIN(id) as min_id
            FROM collation_storage.users
        """,
        "params": [],
        "read_only": True,
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            stats = result["data"]["rows"][0]
            print("✅ Aggregate query successful!")
            print(f"   Statistics: {json.dumps(stats, indent=6)}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_join_query():
    """Test JOIN query (if multiple tables exist)"""
    print("\n" + "=" * 60)
    print("🔗 Testing JOIN Query")
    print("=" * 60)

    # This will work if there are related tables, otherwise it's a self-join example
    data = {
        "database": DATABASE,
        "query": """
            SELECT
                u1.name as user_name,
                COUNT(u2.id) as similar_users
            FROM collation_storage.users u1
            LEFT JOIN collation_storage.users u2
                ON u2.name LIKE CONCAT('%', SUBSTRING(u1.name FROM 1 FOR 3), '%')
                AND u2.id != u1.id
            GROUP BY u1.id, u1.name
            LIMIT 5
        """,
        "params": [],
        "read_only": True,
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ JOIN query successful!")
            print(f"   Found {result['data']['row_count']} groups")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print("   Note: This query requires appropriate table structure")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_read_only_protection():
    """Test that write operations fail when read_only=True"""
    print("\n" + "=" * 60)
    print("🛡️ Testing Read-Only Protection")
    print("=" * 60)

    data = {
        "database": DATABASE,
        "query": "UPDATE collation_storage.users SET name = 'Test' WHERE id = 1",
        "params": [],
        "read_only": True,  # Should reject UPDATE
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 400:
            print("✅ Read-only protection working! UPDATE correctly rejected")
            return True
        elif response.status_code == 200:
            print("❌ Read-only protection failed! UPDATE was allowed")
            return False
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_complex_query():
    """Test complex query with CTEs"""
    print("\n" + "=" * 60)
    print("🎯 Testing Complex Query with CTE")
    print("=" * 60)

    data = {
        "database": DATABASE,
        "query": """
            WITH user_stats AS (
                SELECT
                    COUNT(*) as total,
                    MAX(id) as max_id
                FROM collation_storage.users
            )
            SELECT
                u.id,
                u.name,
                us.total as total_users,
                CASE
                    WHEN u.id = us.max_id THEN 'Latest'
                    ELSE 'Earlier'
                END as user_status
            FROM collation_storage.users u
            CROSS JOIN user_stats us
            ORDER BY u.id DESC
            LIMIT 3
        """,
        "params": [],
        "read_only": True,
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/api/query",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Complex CTE query successful!")
            row_count = result["data"].get("row_count", 0)
            print(f"   Retrieved {row_count} rows")
            if result["data"]["rows"]:
                print(
                    f"   Latest user: {result['data']['rows'][0]['name']} (ID: {result['data']['rows'][0]['id']})"
                )
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("🧪 Testing /api/query Endpoint")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE}")
    print(f"API Endpoint: {BASE_URL}/api/query")

    tests = [
        ("Simple SELECT", test_simple_select),
        ("Parameterized Query", test_parameterized_query),
        ("Aggregate Functions", test_aggregate_query),
        ("JOIN Query", test_join_query),
        ("Read-Only Protection", test_read_only_protection),
        ("Complex CTE Query", test_complex_query),
    ]

    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")

    print("\n" + "=" * 70)
    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
        print("\nThe /api/query endpoint is fully functional with:")
        print("  - Simple and complex SELECT queries")
        print("  - Parameterized queries for SQL injection prevention")
        print("  - Read-only protection when specified")
        print("  - Support for JOINs, CTEs, and aggregations")
    else:
        print(f"⚠️ {passed}/{total} tests passed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
