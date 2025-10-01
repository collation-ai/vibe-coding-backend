#!/bin/bash

# Vibe Auth Gateway Test Script using curl
# This script demonstrates how to test the authentication flow

echo "=========================================="
echo "🧪 Vibe Auth Gateway Test with curl"
echo "=========================================="

# Configuration
GATEWAY_URL="https://vibe-auth-gateway.azurewebsites.net"
USERNAME="tanmais"
PASSWORD="Login123#"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}Test 1: Login${NC}"
echo "----------------------------------------"
echo "POST $GATEWAY_URL/api/auth/login"
echo ""

# Login and capture response with headers
RESPONSE=$(curl -s -i -X POST "$GATEWAY_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

# Extract status code
STATUS=$(echo "$RESPONSE" | grep "HTTP" | awk '{print $2}')

# Extract session cookie
SESSION=$(echo "$RESPONSE" | grep -i "set-cookie:" | sed 's/.*vibe_session=\([^;]*\).*/\1/')

# Extract body (everything after blank line)
BODY=$(echo "$RESPONSE" | sed -n '/^\s*$/,$p' | tail -n +2)

# Parse CSRF token from JSON body
CSRF=$(echo "$BODY" | grep -o '"csrfToken":"[^"]*' | cut -d'"' -f4)

echo "Status Code: $STATUS"

if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Login successful!${NC}"
    echo "Session ID: $SESSION"
    echo "CSRF Token: $CSRF"
    echo "Response Body:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Login failed!${NC}"
    echo "$BODY"
    exit 1
fi

echo ""
echo -e "${BLUE}Test 2: Make Authenticated Request${NC}"
echo "----------------------------------------"
echo "GET $GATEWAY_URL/api/proxy/api/health"
echo ""

# Make authenticated request through proxy
curl -X GET "$GATEWAY_URL/api/proxy/api/health" \
  -H "Cookie: vibe_session=$SESSION" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo -e "${BLUE}Test 3: Test Invalid Session${NC}"
echo "----------------------------------------"
echo "Testing with invalid session..."
echo ""

curl -X GET "$GATEWAY_URL/api/proxy/api/health" \
  -H "Cookie: vibe_session=invalid-session" \
  -H "X-CSRF-Token: invalid-token" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo -e "${BLUE}Test 4: Logout${NC}"
echo "----------------------------------------"
echo "POST $GATEWAY_URL/api/auth/logout"
echo ""

curl -X POST "$GATEWAY_URL/api/auth/logout" \
  -H "Cookie: vibe_session=$SESSION" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Test Complete!${NC}"
echo "=========================================="
echo ""
echo "You can also test manually with:"
echo ""
echo "1. Login:"
echo "   curl -X POST '$GATEWAY_URL/api/auth/login' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}'"
echo ""
echo "2. Use the session cookie and CSRF token from the response for authenticated requests:"
echo "   curl -X GET '$GATEWAY_URL/api/proxy/your/endpoint' \\"
echo "     -H 'Cookie: vibe_session=YOUR_SESSION_ID' \\"
echo "     -H 'X-CSRF-Token: YOUR_CSRF_TOKEN'"
echo ""