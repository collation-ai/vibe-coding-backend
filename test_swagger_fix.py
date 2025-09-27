#!/usr/bin/env python3
"""
Test that Swagger documentation is properly configured
"""

import httpx
import json

BASE_URL = "http://localhost:8000"

def test_swagger_config():
    """Test that Swagger is properly configured"""
    try:
        response = httpx.get(f"{BASE_URL}/openapi.json")
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI spec: {response.status_code}")
            return False
        
        openapi = response.json()
        
        print("\n" + "="*70)
        print("🔍 Checking Swagger Configuration")
        print("="*70 + "\n")
        
        # Check create table endpoint
        create_table_path = openapi["paths"].get("/api/tables", {}).get("post", {})
        
        print("📋 CREATE TABLE Endpoint (/api/tables POST):")
        print("-" * 50)
        
        # Check request body
        if "requestBody" in create_table_path:
            content = create_table_path["requestBody"].get("content", {})
            if "application/json" in content:
                schema_ref = content["application/json"].get("schema", {})
                print("  ✅ Request body is properly defined")
                if "$ref" in schema_ref:
                    schema_name = schema_ref["$ref"].split("/")[-1]
                    print(f"     Schema: {schema_name}")
                    
                    # Check if schema has examples
                    if schema_name in openapi.get("components", {}).get("schemas", {}):
                        schema_def = openapi["components"]["schemas"][schema_name]
                        if "example" in schema_def:
                            print("     ✅ Has example data")
                            print("\n     Example:")
                            print(json.dumps(schema_def["example"], indent=6)[:500])
                        else:
                            print("     ⚠️  No example provided")
            else:
                print("  ❌ No JSON content type")
        else:
            print("  ❌ No request body defined")
        
        # Check parameters
        params = create_table_path.get("parameters", [])
        print("\n  Parameters:")
        if params:
            for param in params:
                name = param.get("name")
                location = param.get("in")
                required = param.get("required", False)
                
                # Check if x_api_key appears as a parameter
                if name and "api" in name.lower():
                    print(f"     ⚠️  {name} in {location} (required: {required})")
                    print("        ^ API key should NOT appear as parameter when using Security scheme")
                else:
                    print(f"     • {name} in {location} (required: {required})")
        else:
            print("     ✅ No parameters (good - API key is in Security scheme)")
        
        # Check security
        if "security" in create_table_path:
            print("\n  Security:")
            print(f"     ✅ {create_table_path['security']}")
        else:
            print("\n  Security:")
            print("     ❌ No security defined")
        
        # Check other endpoints
        print("\n" + "="*70)
        print("📊 Checking All Endpoints for API Key Issues")
        print("="*70 + "\n")
        
        api_key_issues = []
        for path, methods in openapi.get("paths", {}).items():
            for method, details in methods.items():
                if isinstance(details, dict):
                    params = details.get("parameters", [])
                    for param in params:
                        if param.get("name") and "api" in param.get("name", "").lower():
                            api_key_issues.append(f"{method.upper()} {path}")
        
        if api_key_issues:
            print("⚠️  Endpoints with API key as parameter (should use Security instead):")
            for issue in api_key_issues:
                print(f"   - {issue}")
        else:
            print("✅ No endpoints have API key as parameter - all using Security scheme correctly!")
        
        # Check security schemes
        print("\n" + "="*70)
        print("🔐 Security Configuration")
        print("="*70 + "\n")
        
        security_schemes = openapi.get("components", {}).get("securitySchemes", {})
        if security_schemes:
            print("Security Schemes:")
            for name, scheme in security_schemes.items():
                print(f"  • {name}:")
                print(f"    - Type: {scheme.get('type')}")
                print(f"    - In: {scheme.get('in')}")
                print(f"    - Name: {scheme.get('name')}")
                print(f"    - Description: {scheme.get('description', 'N/A')}")
        else:
            print("❌ No security schemes defined")
        
        print("\n" + "="*70)
        print("✅ Swagger configuration check complete!")
        print("\n🎯 Next steps:")
        print("1. Restart the server to apply changes")
        print("2. Go to http://localhost:8000/docs")
        print("3. Use the Authorize button (no API key in individual endpoints)")
        print("4. Test the Create Table endpoint with clear request body")
        print("="*70 + "\n")
        
        return len(api_key_issues) == 0
        
    except Exception as e:
        print(f"❌ Error testing Swagger config: {e}")
        return False

if __name__ == "__main__":
    test_swagger_config()