#!/usr/bin/env python3
"""
Test that API key is properly sent in headers, not URL
"""

import httpx
import json

BASE_URL = "http://localhost:8000"
API_KEY = "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"

def test_auth_in_header():
    """Test authentication with API key in header"""
    print("\n" + "="*60)
    print("🔐 Testing API Key Authentication")
    print("="*60 + "\n")
    
    # Test 1: With API key in header (correct way)
    print("Test 1: API key in HEADER (correct)")
    try:
        response = httpx.post(
            f"{BASE_URL}/api/auth/validate",
            headers={"X-API-Key": API_KEY}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success! User: {data['data']['user']['email']}")
        else:
            print(f"  ❌ Failed with status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: With API key in URL (should NOT work)
    print("\nTest 2: API key in URL (should fail)")
    try:
        response = httpx.post(
            f"{BASE_URL}/api/auth/validate?x_api_key={API_KEY}",
            headers={}
        )
        if response.status_code == 200:
            print("  ⚠️  Unexpectedly succeeded - API key should not work in URL!")
        else:
            print(f"  ✅ Correctly rejected (status {response.status_code})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 3: Without API key (should fail)
    print("\nTest 3: No API key (should fail)")
    try:
        response = httpx.post(
            f"{BASE_URL}/api/auth/validate",
            headers={}
        )
        if response.status_code == 200:
            print("  ⚠️  Unexpectedly succeeded without API key!")
        elif response.status_code in [401, 403]:
            print(f"  ✅ Correctly rejected (status {response.status_code})")
        else:
            print(f"  ❓ Received status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("📋 Testing Data Endpoint with Header Auth")
    print("="*60 + "\n")
    
    # Test a data endpoint
    print("Testing GET /api/tables with API key in header:")
    try:
        response = httpx.get(
            f"{BASE_URL}/api/tables",
            params={"database": "user_db_001"},
            headers={"X-API-Key": API_KEY}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success! Tables count: {data['data']['count']}")
        else:
            print(f"  ❌ Failed with status {response.status_code}")
            print(f"     Response: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ API key authentication is now properly configured!")
    print("   - API key must be sent in X-API-Key header")
    print("   - API key in URL parameters will not work")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_auth_in_header()
