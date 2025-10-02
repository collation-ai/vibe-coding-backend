#!/bin/bash

echo "=========================================="
echo "LOCAL BACKEND TEST SCRIPT"
echo "Tests the backend running locally on port 8000"
echo "=========================================="

# Check if server is running
echo -e "\n1. Checking if local server is running..."
if curl -s http://localhost:8000/api/auth/permissions -o /dev/null -w "%{http_code}" | grep -q "401"; then
    echo "   ✅ Server is running (got 401 as expected without API key)"
else
    echo "   ❌ Server not running. Start it with: python3 run_local_server.py"
    exit 1
fi

# Test 1: Get tanmais permissions (no X-User-Id)
echo -e "\n2. Testing tanmais permissions (default user)..."
response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/auth/permissions \
  -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ")

status=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$status" = "200" ]; then
    echo "   ✅ SUCCESS (Status: $status)"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -10
else
    echo "   ❌ FAILED (Status: $status)"
    echo "$body" | head -3
fi

# Test 2: Get freshwaterapiuser permissions (with X-User-Id)
echo -e "\n3. Testing freshwaterapiuser permissions (via X-User-Id)..."
response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/auth/permissions \
  -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \
  -H "X-User-Id: d4a34dc6-6699-4183-b068-6c7832291e4b")

status=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$status" = "200" ]; then
    echo "   ✅ SUCCESS (Status: $status)"
    echo "$body" | python3 -m json.tool 2>/dev/null | grep -A2 "database"
else
    echo "   ❌ FAILED (Status: $status)"
    echo "$body" | head -3
fi

# Test 3: Test query endpoint
echo -e "\n4. Testing query endpoint..."
response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/query \
  -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "master_db",
    "query": "SELECT COUNT(*) as count FROM users",
    "params": []
  }')

status=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$status" = "200" ]; then
    echo "   ✅ SUCCESS (Status: $status)"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -10
else
    echo "   ❌ FAILED (Status: $status)"
    echo "$body" | head -3
fi

echo -e "\n=========================================="
echo "LOCAL TESTING COMPLETE"
echo "If all tests show ✅, the code is ready for Azure deployment"
echo "=========================================="