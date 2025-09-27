#!/usr/bin/env python3
"""
Quick test to verify all endpoints are available in Swagger
"""

import httpx
import json

BASE_URL = "http://localhost:8000"

def test_openapi():
    """Test that OpenAPI spec contains all endpoints"""
    try:
        response = httpx.get(f"{BASE_URL}/openapi.json")
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI spec: {response.status_code}")
            return False
        
        openapi = response.json()
        
        # Expected endpoints
        expected_endpoints = [
            ("/api/health", ["get"]),
            ("/api/auth/validate", ["post"]),
            ("/api/auth/permissions", ["get"]),
            ("/api/tables", ["post", "get"]),
            ("/api/tables/{table}/structure", ["get"]),
            ("/api/tables/{table}", ["delete"]),
            ("/api/data/{schema}/{table}", ["get", "post", "put", "delete"]),
            ("/api/query", ["post"])
        ]
        
        print("\n" + "="*60)
        print("📋 Checking OpenAPI Endpoints")
        print("="*60 + "\n")
        
        # Check for security schemes (for Authorize button)
        has_auth = False
        if "components" in openapi and "securitySchemes" in openapi["components"]:
            if "APIKeyHeader" in openapi["components"]["securitySchemes"]:
                has_auth = True
                print("✅ API Key authentication configured (Authorize button available)")
            else:
                print("❌ API Key authentication not configured")
        else:
            print("❌ No security schemes defined")
        
        print("\n📍 Endpoints found in OpenAPI spec:\n")
        
        # Check each endpoint
        paths = openapi.get("paths", {})
        missing = []
        
        for path, methods in expected_endpoints:
            if path in paths:
                available_methods = list(paths[path].keys())
                for method in methods:
                    if method in available_methods:
                        print(f"  ✅ {method.upper():6} {path}")
                    else:
                        print(f"  ❌ {method.upper():6} {path} - Method missing")
                        missing.append(f"{method.upper()} {path}")
            else:
                print(f"  ❌ {path} - Endpoint missing entirely")
                for method in methods:
                    missing.append(f"{method.upper()} {path}")
        
        # Show summary
        print("\n" + "="*60)
        total_paths = len(paths)
        print(f"📊 Total endpoints in spec: {total_paths}")
        
        if missing:
            print(f"\n⚠️  Missing endpoints: {len(missing)}")
            for m in missing:
                print(f"   - {m}")
        else:
            print("\n✅ All expected endpoints are available!")
        
        # Show all available paths for reference
        if len(paths) > len(expected_endpoints):
            print("\n📌 Additional endpoints found:")
            for path in paths:
                if not any(path == ep[0] for ep in expected_endpoints):
                    methods = ", ".join(paths[path].keys()).upper()
                    print(f"   - {methods} {path}")
        
        print("="*60)
        
        return len(missing) == 0 and has_auth
        
    except Exception as e:
        print(f"❌ Error testing OpenAPI: {e}")
        return False

def test_swagger_ui():
    """Test that Swagger UI is accessible"""
    try:
        response = httpx.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("\n✅ Swagger UI is accessible at http://localhost:8000/docs")
            return True
        else:
            print(f"\n❌ Swagger UI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error accessing Swagger UI: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 Testing Vibe Coding Backend Endpoints\n")
    
    # Test OpenAPI spec
    openapi_ok = test_openapi()
    
    # Test Swagger UI
    swagger_ok = test_swagger_ui()
    
    # Final result
    print("\n" + "="*60)
    if openapi_ok and swagger_ok:
        print("✅ SUCCESS: All endpoints are available and Swagger is properly configured!")
        print("\n🎯 Next steps:")
        print("1. Restart your server: python3 run_local.py")
        print("2. Open http://localhost:8000/docs")
        print("3. Click the 'Authorize' button (🔒)")
        print("4. Enter your API key: vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA")
        print("5. Test all the endpoints!")
    else:
        print("⚠️  Some issues found. Please restart the server with:")
        print("   1. Stop current server (Ctrl+C)")
        print("   2. Run: python3 run_local.py")
    print("="*60 + "\n")