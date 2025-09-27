#!/usr/bin/env python3
"""Test script to verify API endpoints are working"""

import asyncio
import httpx
import json
import sys

# Test configuration
API_KEY = "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"  # Replace with your API key
BASE_URL = "http://localhost:3000"  # Local development URL

async def test_auth_validate():
    """Test API key validation"""
    print("Testing /api/auth/validate...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/validate",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Authentication successful!")
            print(f"   User: {data['data']['user']['email']}")
            print(f"   Permissions: {len(data['data']['permissions'])} schema(s)")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

async def test_health():
    """Test health endpoint"""
    print("\nTesting /api/health...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/health")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {data['status']}")
            print(f"   Database: {'Connected' if data['database'] else 'Not connected'}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False

async def test_list_tables():
    """Test listing tables"""
    print("\nTesting /api/tables (list tables)...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/tables",
            params={"database": "user_db_001", "schema": "public"},
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Table listing successful!")
            print(f"   Tables found: {data['data']['count']}")
            return True
        else:
            print(f"❌ Table listing failed: {response.status_code}")
            if response.status_code == 403:
                print("   Note: Check if user_db_001 exists and is properly configured")
            return False

async def test_create_table():
    """Test creating a table"""
    print("\nTesting /api/tables (create table)...")
    
    table_request = {
        "database": "user_db_001",
        "schema": "public",
        "table": "test_users",
        "columns": [
            {
                "name": "id",
                "type": "SERIAL",
                "constraints": ["PRIMARY KEY"]
            },
            {
                "name": "email",
                "type": "VARCHAR(255)",
                "constraints": ["UNIQUE", "NOT NULL"]
            },
            {
                "name": "created_at",
                "type": "TIMESTAMP",
                "default": "NOW()"
            }
        ],
        "if_not_exists": True
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/tables",
            json=table_request,
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("✅ Table creation successful!")
            print(f"   Table: {data['data']['schema']}.{data['data']['table']}")
            return True
        else:
            print(f"❌ Table creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

async def main():
    print("="*50)
    print("Vibe Coding Backend API Test")
    print("="*50)
    print(f"API Key: {API_KEY[:20]}...")
    print(f"Base URL: {BASE_URL}")
    print("="*50)
    
    # Run tests
    tests = [
        test_health,
        test_auth_validate,
        # test_list_tables,  # Uncomment when user_db_001 is configured
        # test_create_table,  # Uncomment when user_db_001 is configured
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Error running test: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the configuration.")
        print("\nNote: Table operations require user_db_001 to be configured.")
        print("Add the database connection in database_assignments table.")
    
    print("="*50)

if __name__ == "__main__":
    # Check if running locally
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    asyncio.run(main())
