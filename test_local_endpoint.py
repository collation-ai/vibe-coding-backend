#!/usr/bin/env python3
"""
Test the actual local endpoint code
"""

import asyncio
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.auth.validate import app

# Create test client
client = TestClient(app)


def test_permissions_endpoint():
    """Test the permissions endpoint locally"""

    print("=" * 60)
    print("TESTING LOCAL ENDPOINT (not Azure)")
    print("=" * 60)

    # Test without X-User-Id
    print("\n1. Testing WITHOUT X-User-Id header:")
    response = client.get(
        "/api/auth/permissions",
        headers={"X-API-Key": "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"},
    )

    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(
            f"   ✅ SUCCESS! Got {len(data.get('data', {}).get('permissions', []))} permissions"
        )
        print(f"   Databases: {data.get('data', {}).get('databases', [])}")
    else:
        print(f"   ❌ ERROR: {response.text[:200]}")

    # Test with X-User-Id
    print("\n2. Testing WITH X-User-Id header (freshwaterapiuser):")
    response = client.get(
        "/api/auth/permissions",
        headers={
            "X-API-Key": "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            "X-User-Id": "d4a34dc6-6699-4183-b068-6c7832291e4b",
        },
    )

    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(
            f"   ✅ SUCCESS! Got {len(data.get('data', {}).get('permissions', []))} permissions"
        )
        print(f"   Databases: {data.get('data', {}).get('databases', [])}")
    else:
        print(f"   ❌ ERROR: {response.text[:200]}")

    print("\n" + "=" * 60)
    print("If both tests show ✅ SUCCESS, your local fix is working!")
    print("The Azure deployment still needs to be updated.")
    print("=" * 60)


if __name__ == "__main__":
    test_permissions_endpoint()
