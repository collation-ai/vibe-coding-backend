#!/usr/bin/env python3
"""
Complete test suite for Vibe Coding Backend API
Tests all CRUD operations and features
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

# Test configuration - UPDATE THESE
API_KEY = "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"  # Your API key
BASE_URL = "http://localhost:8000"
TEST_DATABASE = "user_db_001"  # Your test database
TEST_SCHEMA = "public"

# Test data
TEST_TABLE = f"test_table_{int(datetime.now().timestamp())}"


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name: str, status: bool, message: str = ""):
    icon = f"{Colors.GREEN}✅{Colors.END}" if status else f"{Colors.RED}❌{Colors.END}"
    status_text = f"{Colors.GREEN}PASSED{Colors.END}" if status else f"{Colors.RED}FAILED{Colors.END}"
    print(f"{icon} {name}: {status_text}")
    if message:
        print(f"   {message}")


async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/health")
            success = response.status_code == 200
            data = response.json()
            print_test("Health Check", success, f"Status: {data.get('status', 'unknown')}")
            return success
        except Exception as e:
            print_test("Health Check", False, str(e))
            return False


async def test_auth_validate():
    """Test API key validation"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/auth/validate",
                headers={"X-API-Key": API_KEY}
            )
            success = response.status_code == 200
            if success:
                data = response.json()
                user_email = data['data']['user']['email']
                print_test("Auth Validation", success, f"User: {user_email}")
            else:
                print_test("Auth Validation", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("Auth Validation", False, str(e))
            return False


async def test_create_table():
    """Test table creation"""
    async with httpx.AsyncClient() as client:
        try:
            table_request = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "columns": [
                    {
                        "name": "id",
                        "type": "SERIAL",
                        "constraints": ["PRIMARY KEY"]
                    },
                    {
                        "name": "name",
                        "type": "VARCHAR(100)",
                        "constraints": ["NOT NULL"]
                    },
                    {
                        "name": "email",
                        "type": "VARCHAR(255)",
                        "constraints": ["UNIQUE"]
                    },
                    {
                        "name": "age",
                        "type": "INTEGER"
                    },
                    {
                        "name": "created_at",
                        "type": "TIMESTAMP",
                        "default": "NOW()"
                    }
                ],
                "if_not_exists": True
            }
            
            response = await client.post(
                f"{BASE_URL}/api/tables",
                json=table_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code in [200, 201]
            if success:
                print_test("Create Table", success, f"Table: {TEST_SCHEMA}.{TEST_TABLE}")
            else:
                print_test("Create Table", False, f"Status: {response.status_code}, Error: {response.text}")
            return success
        except Exception as e:
            print_test("Create Table", False, str(e))
            return False


async def test_list_tables():
    """Test listing tables"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/tables",
                params={"database": TEST_DATABASE, "schema": TEST_SCHEMA},
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                table_count = data['data']['count']
                print_test("List Tables", success, f"Found {table_count} tables")
            else:
                print_test("List Tables", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("List Tables", False, str(e))
            return False


async def test_insert_data():
    """Test data insertion"""
    async with httpx.AsyncClient() as client:
        try:
            # Insert single record
            insert_request = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                },
                "returning": ["id", "name", "created_at"]
            }
            
            response = await client.post(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                json=insert_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code in [200, 201]
            if success:
                data = response.json()
                print_test("Insert Single Record", success, f"Inserted {data['data']['inserted']} record")
            else:
                print_test("Insert Single Record", False, f"Status: {response.status_code}")
            
            # Insert multiple records
            bulk_insert = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "data": [
                    {"name": "Jane Smith", "email": "jane@example.com", "age": 25},
                    {"name": "Bob Johnson", "email": "bob@example.com", "age": 35},
                    {"name": "Alice Brown", "email": "alice@example.com", "age": 28}
                ]
            }
            
            response = await client.post(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                json=bulk_insert,
                headers={"X-API-Key": API_KEY}
            )
            
            bulk_success = response.status_code in [200, 201]
            if bulk_success:
                data = response.json()
                print_test("Insert Bulk Records", bulk_success, f"Inserted {data['data']['inserted']} records")
            else:
                print_test("Insert Bulk Records", False, f"Status: {response.status_code}")
            
            return success and bulk_success
        except Exception as e:
            print_test("Insert Data", False, str(e))
            return False


async def test_query_data():
    """Test data querying"""
    async with httpx.AsyncClient() as client:
        try:
            # Simple query
            response = await client.get(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                params={
                    "database": TEST_DATABASE,
                    "limit": 10,
                    "offset": 0
                },
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                row_count = data['data']['row_count']
                print_test("Query All Data", success, f"Retrieved {row_count} rows")
            else:
                print_test("Query All Data", False, f"Status: {response.status_code}")
            
            # Query with filter
            where_conditions = json.dumps({"age": 30})
            response = await client.get(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                params={
                    "database": TEST_DATABASE,
                    "where": where_conditions,
                    "select": "id,name,email,age"
                },
                headers={"X-API-Key": API_KEY}
            )
            
            filter_success = response.status_code == 200
            if filter_success:
                data = response.json()
                row_count = data['data']['row_count']
                print_test("Query With Filter", filter_success, f"Found {row_count} matching rows")
            else:
                print_test("Query With Filter", False, f"Status: {response.status_code}")
            
            return success and filter_success
        except Exception as e:
            print_test("Query Data", False, str(e))
            return False


async def test_update_data():
    """Test data update"""
    async with httpx.AsyncClient() as client:
        try:
            update_request = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "set": {"age": 31},
                "where": {"name": "John Doe"}
            }
            
            response = await client.put(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                json=update_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                affected = data['data'].get('affected_rows', 0)
                print_test("Update Data", success, f"Updated {affected} rows")
            else:
                print_test("Update Data", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("Update Data", False, str(e))
            return False


async def test_raw_query():
    """Test raw SQL query execution"""
    async with httpx.AsyncClient() as client:
        try:
            query_request = {
                "database": TEST_DATABASE,
                "query": f"SELECT COUNT(*) as total, AVG(age) as avg_age FROM {TEST_SCHEMA}.{TEST_TABLE}",
                "params": [],
                "read_only": True
            }
            
            response = await client.post(
                f"{BASE_URL}/api/query",
                json=query_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                rows = data['data']['rows']
                if rows:
                    total = rows[0]['total']
                    avg_age = rows[0]['avg_age']
                    print_test("Raw Query", success, f"Total: {total}, Avg Age: {avg_age}")
                else:
                    print_test("Raw Query", success, "Query executed")
            else:
                print_test("Raw Query", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("Raw Query", False, str(e))
            return False


async def test_delete_data():
    """Test data deletion"""
    async with httpx.AsyncClient() as client:
        try:
            delete_request = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "where": {"name": "Bob Johnson"},
                "returning": ["id", "name"]
            }
            
            response = await client.delete(
                f"{BASE_URL}/api/data/{TEST_SCHEMA}/{TEST_TABLE}",
                json=delete_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                affected = data['data'].get('affected_rows', 0)
                print_test("Delete Data", success, f"Deleted {affected} rows")
            else:
                print_test("Delete Data", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("Delete Data", False, str(e))
            return False


async def test_drop_table():
    """Test table deletion"""
    async with httpx.AsyncClient() as client:
        try:
            drop_request = {
                "database": TEST_DATABASE,
                "schema": TEST_SCHEMA,
                "table": TEST_TABLE,
                "if_exists": True
            }
            
            response = await client.delete(
                f"{BASE_URL}/api/tables/{TEST_TABLE}",
                json=drop_request,
                headers={"X-API-Key": API_KEY}
            )
            
            success = response.status_code == 200
            if success:
                print_test("Drop Table", success, f"Dropped table {TEST_TABLE}")
            else:
                print_test("Drop Table", False, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_test("Drop Table", False, str(e))
            return False


async def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("VIBE CODING BACKEND - COMPLETE TEST SUITE")
    print(f"{'='*60}{Colors.END}\n")
    
    print(f"Configuration:")
    print(f"  API URL: {BASE_URL}")
    print(f"  Database: {TEST_DATABASE}")
    print(f"  Schema: {TEST_SCHEMA}")
    print(f"  Test Table: {TEST_TABLE}")
    print(f"  API Key: {API_KEY[:20]}...")
    print()
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{BASE_URL}/api/health", timeout=2)
    except:
        print(f"{Colors.RED}❌ Server is not running at {BASE_URL}{Colors.END}")
        print(f"\nPlease start the server first:")
        print(f"  python main.py")
        return
    
    tests = [
        ("System Health", test_health),
        ("Authentication", test_auth_validate),
        ("Table Creation", test_create_table),
        ("List Tables", test_list_tables),
        ("Insert Data", test_insert_data),
        ("Query Data", test_query_data),
        ("Update Data", test_update_data),
        ("Raw SQL Query", test_raw_query),
        ("Delete Data", test_delete_data),
        ("Drop Table", test_drop_table),
    ]
    
    print(f"{Colors.YELLOW}Running tests...{Colors.END}\n")
    
    results = []
    for name, test_func in tests:
        result = await test_func()
        results.append((name, result))
        await asyncio.sleep(0.1)  # Small delay between tests
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASSED{Colors.END}" if result else f"{Colors.RED}FAILED{Colors.END}"
        print(f"  {name}: {status}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}✅ ALL TESTS PASSED! ({passed}/{total}){Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  Some tests failed: {passed}/{total} passed{Colors.END}")
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")


if __name__ == "__main__":
    # Check if database name is provided as argument
    if len(sys.argv) > 1:
        TEST_DATABASE = sys.argv[1]
    
    asyncio.run(main())