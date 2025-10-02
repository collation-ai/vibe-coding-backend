#!/usr/bin/env python3
"""
Local test script to simulate the gateway proxy behavior
This helps debug issues without deploying to Azure
"""

import asyncio
import asyncpg
import requests
import json
from datetime import datetime

# Configuration
MASTER_DB_URL = "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
BACKEND_URL = "https://vibe-coding-backend.azurewebsites.net"
GATEWAY_API_KEY = "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"  # The gateway's API key

async def get_session_info(session_id):
    """Simulate getting session info (in real gateway this is from Azure Table Storage)"""
    # For testing, we'll get the user info from the database
    # In production, this would come from Azure Table Storage
    
    conn = await asyncpg.connect(MASTER_DB_URL)
    
    # For this test, let's assume the session belongs to freshwaterapiuser
    # In reality, you'd look this up in Azure Table Storage
    user = await conn.fetchrow("""
        SELECT id, username, email, organization
        FROM users 
        WHERE username = 'freshwaterapiuser'
    """)
    
    await conn.close()
    
    if user:
        return {
            "userId": str(user['id']),
            "username": user['username'],
            "email": user['email']
        }
    return None

def test_permissions_endpoint(user_id, username):
    """Test the permissions endpoint as the gateway would call it"""
    
    print(f"\n{'='*60}")
    print(f"Testing permissions endpoint for user: {username}")
    print(f"User ID: {user_id}")
    print(f"{'='*60}\n")
    
    # This simulates what the gateway proxy does
    headers = {
        'X-API-Key': GATEWAY_API_KEY,
        'X-User-Id': user_id,
        'X-Username': username,
        'Content-Type': 'application/json'
    }
    
    url = f"{BACKEND_URL}/api/auth/permissions"
    
    print(f"Calling: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nSuccess! Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\nError Response:")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 10 seconds")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def test_query_endpoint(user_id, username):
    """Test the query endpoint as the gateway would call it"""
    
    print(f"\n{'='*60}")
    print(f"Testing query endpoint for user: {username}")
    print(f"User ID: {user_id}")
    print(f"{'='*60}\n")
    
    headers = {
        'X-API-Key': GATEWAY_API_KEY,
        'X-User-Id': user_id,
        'X-Username': username,
        'Content-Type': 'application/json'
    }
    
    body = {
        "database": "master_db",
        "query": "SELECT COUNT(*) as user_count FROM users",
        "params": []
    }
    
    url = f"{BACKEND_URL}/api/query"
    
    print(f"Calling: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nSuccess! Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\nError Response:")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 10 seconds")
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def main():
    print("="*60)
    print("LOCAL GATEWAY PROXY TESTING")
    print("="*60)
    
    # Simulate a session for freshwaterapiuser
    session_info = await get_session_info("dummy-session-id")
    
    if session_info:
        print(f"\nSession Info:")
        print(f"  User: {session_info['username']}")
        print(f"  User ID: {session_info['userId']}")
        print(f"  Email: {session_info['email']}")
        
        # Test 1: Permissions endpoint
        test_permissions_endpoint(session_info['userId'], session_info['username'])
        
        # Test 2: Query endpoint  
        test_query_endpoint(session_info['userId'], session_info['username'])
    else:
        print("❌ Could not get session info")

if __name__ == "__main__":
    asyncio.run(main())