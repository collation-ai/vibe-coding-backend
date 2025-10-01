#!/bin/bash

echo "=== Authentication Gateway Example Flow ==="
echo ""
echo "Step 1: Login to get session and CSRF token"
echo "--------------------------------------------"

# Login
LOGIN_RESPONSE=$(curl -s -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"tanmais","password":"Login123#"}' \
  -c cookies.txt)

# Extract CSRF token from response
CSRF_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"csrfToken":"[^"]*' | cut -d'"' -f4)

echo "Login Response:"
echo $LOGIN_RESPONSE | python3 -m json.tool
echo ""
echo "CSRF Token: $CSRF_TOKEN"
echo "Session cookie saved to cookies.txt"
echo ""

echo "Step 2: Call backend through proxy (NOT directly!)"
echo "---------------------------------------------------"
echo ""

echo "Example 1: Get permissions"
echo "URL: https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/auth/permissions"
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/auth/permissions" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -b cookies.txt \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "Example 2: Get databases"
echo "URL: https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/databases"
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/databases" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -b cookies.txt \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=== Important Notes ==="
echo "1. CSRF Token is NOT an API key - it's for security"
echo "2. Session cookie (vibe_session) is your authentication"
echo "3. Real API key (vibe_prod_...) is hidden server-side"
echo "4. ALWAYS use /api/proxy/* endpoints, not direct backend URLs"
echo ""
echo "The flow:"
echo "  Browser -> Auth Gateway (with session+CSRF) -> Backend (with real API key)"
echo ""