# How to Use the Authentication Gateway

## Key Concepts

1. **Session Cookie** (`vibe_session`) - Found in the `Set-Cookie` header after login
2. **CSRF Token** - Found in the JSON response body after login  
3. **Proxy Path** - The gateway adds `/api/` to your path automatically

## Step 1: Login and Get Credentials

```bash
curl -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"tanmais","password":"Login123#"}'
```

From the response, extract:
- **Session ID** from header: `set-cookie: vibe_session=xxxxx...`
- **CSRF Token** from body: `"csrfToken": "yyyyy..."`

## Step 2: Use the Proxy

### Important Path Translation

The proxy automatically adds `/api/` to your path:

| Backend Endpoint | Proxy Endpoint |
|-----------------|----------------|
| `/api/health` | `/api/proxy/health` |
| `/api/databases` | `/api/proxy/databases` |
| `/api/tables` | `/api/proxy/tables` |
| `/api/data/public/users` | `/api/proxy/data/public/users` |

### Example Requests

```bash
# Get databases (if backend has /api/databases endpoint)
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/databases" \
  -H "Cookie: vibe_session=YOUR_SESSION_ID" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN"

# Get tables (if backend has /api/tables endpoint)
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/tables" \
  -H "Cookie: vibe_session=YOUR_SESSION_ID" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN"

# Query data from a table
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/data/public/users" \
  -H "Cookie: vibe_session=YOUR_SESSION_ID" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN" \
  -H "X-Database-Name: your_database"
```

## Complete Example with Real Values

```bash
# 1. Login
RESPONSE=$(curl -s -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"tanmais","password":"Login123#"}')

# 2. Extract session and CSRF
SESSION=$(echo "$RESPONSE" | grep -i "set-cookie:" | sed 's/.*vibe_session=\([^;]*\).*/\1/')
CSRF=$(echo "$RESPONSE" | tail -1 | grep -o '"csrfToken":"[^"]*' | cut -d'"' -f4)

echo "Session: $SESSION"
echo "CSRF: $CSRF"

# 3. Make authenticated request
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/databases" \
  -H "Cookie: vibe_session=$SESSION" \
  -H "X-CSRF-Token: $CSRF"
```

## For Lovable.dev Integration

```javascript
// Login and store credentials
const loginResponse = await fetch('https://vibe-auth-gateway.azurewebsites.net/api/auth/login', {
  method: 'POST',
  credentials: 'include', // Important for cookies
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'tanmais', password: 'Login123#' })
});

const { data } = await loginResponse.json();
const csrfToken = data.csrfToken;

// Make authenticated API calls
const apiResponse = await fetch('https://vibe-auth-gateway.azurewebsites.net/api/proxy/databases', {
  credentials: 'include', // Sends the session cookie
  headers: {
    'X-CSRF-Token': csrfToken,
    'Content-Type': 'application/json'
  }
});
```

## Troubleshooting

- **404 Not Found**: The endpoint doesn't exist on the backend
- **401 Unauthorized**: Session expired or invalid
- **403 Forbidden**: CSRF token missing or incorrect
- **500 Internal Server Error**: Check Azure Function logs

Remember: The gateway adds `/api/` to your path, so adjust accordingly!