#!/usr/bin/env python3
"""
Test all data operations after fixing the request schemas
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"

# Test with your actual API key and database
API_KEY = "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
DATABASE = "minerva_pear"
SCHEMA = "collation_storage"
TABLE = "users"

def test_insert_single():
    """Test single record insertion"""
    print("\n" + "="*60)
    print("📝 Testing Single Insert")
    print("="*60)
    
    data = {
        "database": DATABASE,
        "data": {
            "email": f"test_{int(time.time())}@example.com",
            "name": "Test User"
        },
        "returning": ["id", "email", "created_at"]
    }
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Single insert successful!")
            print(f"   Inserted ID: {result['data']['rows'][0]['id']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_insert_bulk():
    """Test bulk record insertion"""
    print("\n" + "="*60)
    print("📝 Testing Bulk Insert")
    print("="*60)
    
    timestamp = int(time.time())
    data = {
        "database": DATABASE,
        "data": [
            {"email": f"bulk1_{timestamp}@example.com", "name": "Bulk User 1"},
            {"email": f"bulk2_{timestamp}@example.com", "name": "Bulk User 2"},
            {"email": f"bulk3_{timestamp}@example.com", "name": "Bulk User 3"}
        ],
        "returning": ["id", "name"]
    }
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        
        if response.status_code == 201:
            result = response.json()
            inserted_count = result['data']['inserted']
            print(f"✅ Bulk insert successful! Inserted {inserted_count} records")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_query():
    """Test data query"""
    print("\n" + "="*60)
    print("🔍 Testing Query")
    print("="*60)
    
    try:
        response = httpx.get(
            f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
            params={
                "database": DATABASE,
                "limit": 5,
                "order_by": "id",
                "order": "DESC"
            },
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        
        if response.status_code == 200:
            result = response.json()
            row_count = result['data']['row_count']
            print(f"✅ Query successful! Retrieved {row_count} rows")
            if row_count > 0:
                print(f"   Latest user: {result['data']['rows'][0].get('name', 'N/A')}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_update():
    """Test data update"""
    print("\n" + "="*60)
    print("✏️ Testing Update")
    print("="*60)
    
    data = {
        "database": DATABASE,
        "set": {"name": "Updated Name"},
        "where": {"email": "john@example.com"},
        "returning": ["id", "name", "email"]
    }
    
    try:
        response = httpx.put(
            f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
            json=data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        
        if response.status_code == 200:
            result = response.json()
            affected = result['data'].get('affected_rows', 0)
            print(f"✅ Update successful! Updated {affected} rows")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_delete():
    """Test data deletion"""
    print("\n" + "="*60)
    print("🗑️ Testing Delete")
    print("="*60)
    
    # First insert a test record to delete
    timestamp = int(time.time())
    test_email = f"delete_test_{timestamp}@example.com"
    
    # Insert
    insert_data = {
        "database": DATABASE,
        "data": {"email": test_email, "name": "To Delete"},
    }
    
    insert_resp = httpx.post(
        f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
        json=insert_data,
        headers={"X-API-Key": API_KEY},
        timeout=10.0
    )
    
    if insert_resp.status_code != 201:
        print("❌ Failed to insert test record for deletion")
        return False
    
    # Delete
    delete_data = {
        "database": DATABASE,
        "where": {"email": test_email},
        "returning": ["id", "email"]
    }
    
    try:
        response = httpx.request(
            "DELETE",
            f"{BASE_URL}/api/data/{SCHEMA}/{TABLE}",
            json=delete_data,
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        
        if response.status_code == 200:
            result = response.json()
            affected = result['data'].get('affected_rows', 0)
            print(f"✅ Delete successful! Deleted {affected} rows")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🧪 Testing Data Operations with Fixed Request Schemas")
    print("="*70)
    print(f"\nDatabase: {DATABASE}")
    print(f"Schema: {SCHEMA}")
    print(f"Table: {TABLE}")
    
    tests = [
        ("Single Insert", test_insert_single),
        ("Bulk Insert", test_insert_bulk),
        ("Query Data", test_query),
        ("Update Data", test_update),
        ("Delete Data", test_delete)
    ]
    
    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    print("\n" + "="*70)
    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
        print("\nThe data operations are working correctly with the fixed schemas.")
        print("Schema and table parameters are now properly handled from URL paths.")
    else:
        print(f"⚠️ {passed}/{total} tests passed")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
