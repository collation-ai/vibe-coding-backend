#!/usr/bin/env python3
"""
Test that the create table endpoint works after fixing JSON serialization
"""

import httpx
import json

BASE_URL = "http://localhost:8000"
API_KEY = "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"


def test_create_table():
    """Test creating a table with the fixed endpoint"""
    print("\n" + "=" * 60)
    print("🔧 Testing Create Table Endpoint")
    print("=" * 60 + "\n")

    # Test table creation
    create_request = {
        "database": "user_db_001",
        "schema": "public",
        "table": "test_users",
        "columns": [
            {"name": "id", "type": "SERIAL", "constraints": ["PRIMARY KEY"]},
            {
                "name": "email",
                "type": "VARCHAR(255)",
                "constraints": ["UNIQUE", "NOT NULL"],
            },
            {"name": "username", "type": "VARCHAR(100)", "constraints": ["NOT NULL"]},
            {"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"},
        ],
        "if_not_exists": True,
    }

    print("Request body:")
    print(json.dumps(create_request, indent=2))
    print("\nSending request...")

    try:
        response = httpx.post(
            f"{BASE_URL}/api/tables",
            json=create_request,
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 201:
            data = response.json()
            print("✅ Table created successfully!")
            print(f"\nResponse: {json.dumps(data, indent=2)}")

            # Check if timestamp is properly formatted
            if "metadata" in data and "timestamp" in data["metadata"]:
                print(
                    f"\n✅ Timestamp properly serialized: {data['metadata']['timestamp']}"
                )
        elif response.status_code == 500:
            print("❌ Internal server error")
            print(f"Response: {response.text[:500]}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")

        return response.status_code in [200, 201]

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_list_tables():
    """Test listing tables to verify creation"""
    print("\n" + "=" * 60)
    print("📋 Testing List Tables Endpoint")
    print("=" * 60 + "\n")

    try:
        response = httpx.get(
            f"{BASE_URL}/api/tables",
            params={"database": "user_db_001", "schema": "public"},
            headers={"X-API-Key": API_KEY},
            timeout=10.0,
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Tables listed successfully!")

            # Check if our test table exists
            if "data" in data and "tables" in data["data"]:
                tables = data["data"]["tables"]
                if any(t.get("table_name") == "test_users" for t in tables):
                    print("✅ Test table 'test_users' found in the list")
                else:
                    print("⚠️  Test table 'test_users' not found in the list")

                print(f"\nTotal tables: {data['data']['count']}")
                for table in tables[:5]:  # Show first 5 tables
                    print(f"  - {table.get('table_name')}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")

        return response.status_code == 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 Testing Fixed Create Table Endpoint\n")

    # Test create table
    create_success = test_create_table()

    # Test list tables
    list_success = test_list_tables()

    print("\n" + "=" * 60)
    if create_success and list_success:
        print("✅ All tests passed! JSON serialization issue is fixed.")
        print("\nThe datetime serialization error has been resolved.")
        print("Tables can now be created successfully via Swagger UI.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    print("=" * 60 + "\n")
