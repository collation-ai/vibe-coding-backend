#!/usr/bin/env python3
"""
Test the backend directly to isolate the issue
"""

import requests
import json

BACKEND_URL = "https://vibe-coding-backend.azurewebsites.net"
API_KEY = "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"

def test_without_user_id():
    """Test permissions without X-User-Id header"""
    print("\n" + "="*60)
    print("TEST 1: Without X-User-Id header (should return tanmais's permissions)")
    print("="*60)
    
    headers = {
        'X-API-Key': API_KEY
    }
    
    url = f"{BACKEND_URL}/api/auth/permissions"
    
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Databases: {data.get('data', {}).get('databases', [])}")
            permissions = data.get('data', {}).get('permissions', [])
            for perm in permissions[:3]:  # Show first 3 permissions
                print(f"  - {perm.get('database')}.{perm.get('schema')}: {perm.get('permission')}")
        else:
            print(f"❌ ERROR: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Request timed out!")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_with_user_id():
    """Test permissions with X-User-Id header"""
    print("\n" + "="*60)
    print("TEST 2: With X-User-Id header (should return freshwaterapiuser's permissions)")
    print("="*60)
    
    headers = {
        'X-API-Key': API_KEY,
        'X-User-Id': 'd4a34dc6-6699-4183-b068-6c7832291e4b'  # freshwaterapiuser
    }
    
    url = f"{BACKEND_URL}/api/auth/permissions"
    
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Databases: {data.get('data', {}).get('databases', [])}")
            permissions = data.get('data', {}).get('permissions', [])
            for perm in permissions:
                print(f"  - {perm.get('database')}.{perm.get('schema')}: {perm.get('permission')}")
        else:
            print(f"❌ ERROR: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Request timed out!")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health():
    """Test health endpoint to verify backend is up"""
    print("\n" + "="*60)
    print("TEST 0: Health check")
    print("="*60)
    
    url = f"{BACKEND_URL}/api/health"
    headers = {'X-API-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Backend is healthy")
        else:
            print(f"❌ Backend health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("TESTING BACKEND DIRECTLY")
    print("="*60)
    
    # Test 0: Health check
    test_health()
    
    # Test 1: Without X-User-Id
    test_without_user_id()
    
    # Test 2: With X-User-Id
    test_with_user_id()