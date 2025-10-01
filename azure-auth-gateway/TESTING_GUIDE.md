# Testing the Azure Authentication Gateway

## Quick Test Commands

### 1. Test Login (Get Session and CSRF Token)

```bash
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"tanmais","password":"Login123#"}' \
  -i
```

**Expected Response:**
- Status: 200 OK
- Set-Cookie header with `vibe_session` cookie
- JSON body with `csrfToken`, `username`, `email`, etc.

Example:
```
HTTP/1.1 200 OK
Set-Cookie: vibe_session=abc123...; HttpOnly; Secure
Content-Type: application/json

{
  "success": true,
  "data": {
    "csrfToken": "xyz789...",
    "username": "tanmais",
    "email": "tanmais@vibe-coding.com",
    "expiresIn": 3600
  }
}
```

### 2. Test Authenticated Proxy Request

After login, use the session cookie and CSRF token:

```bash
# Replace SESSION_ID and CSRF_TOKEN with values from login response
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/health" \
  -H "Cookie: vibe_session=SESSION_ID" \
  -H "X-CSRF-Token: CSRF_TOKEN" \
  -H "Content-Type: application/json"
```

### 3. Test Logout

```bash
# Use same session and CSRF token
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/logout" \
  -H "Cookie: vibe_session=SESSION_ID" \
  -H "X-CSRF-Token: CSRF_TOKEN" \
  -H "Content-Type: application/json"
```

## Automated Testing

### Node.js Test Script

Run the complete test suite:

```bash
# Interactive mode (prompts for username/password)
node test-complete-flow.js

# Quick mode (uses default credentials)
node test-complete-flow.js --quick
```

### Python Test Example

```python
import requests

# 1. Login
login_response = requests.post(
    "https://vibe-auth-gateway.azurewebsites.net/api/auth/login",
    json={"username": "tanmais", "password": "Login123#"}
)

if login_response.status_code == 200:
    session_cookie = login_response.cookies.get("vibe_session")
    csrf_token = login_response.json()["data"]["csrfToken"]
    print(f"✅ Logged in! Session: {session_cookie}, CSRF: {csrf_token}")
    
    # 2. Make authenticated request
    proxy_response = requests.get(
        "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/health",
        cookies={"vibe_session": session_cookie},
        headers={"X-CSRF-Token": csrf_token}
    )
    print(f"Proxy response: {proxy_response.status_code}")
    
    # 3. Logout
    logout_response = requests.post(
        "https://vibe-auth-gateway.azurewebsites.net/api/auth/logout",
        cookies={"vibe_session": session_cookie},
        headers={"X-CSRF-Token": csrf_token}
    )
    print(f"Logout response: {logout_response.status_code}")
```

## Browser Testing

### Using Browser DevTools

1. Open browser DevTools (F12)
2. Go to Network tab
3. Make login request:

```javascript
fetch('https://vibe-auth-gateway.azurewebsites.net/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    username: 'tanmais',
    password: 'Login123#'
  })
})
.then(r => r.json())
.then(data => {
  console.log('CSRF Token:', data.data.csrfToken);
  window.csrfToken = data.data.csrfToken;
});
```

4. Make authenticated request:

```javascript
fetch('https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/health', {
  method: 'GET',
  credentials: 'include',
  headers: {
    'X-CSRF-Token': window.csrfToken,
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(console.log);
```

## Testing from Lovable.dev

In your Lovable.dev application, implement the authentication service:

```typescript
class AuthService {
  private csrfToken: string | null = null;
  private baseUrl = 'https://vibe-auth-gateway.azurewebsites.net';

  async login(username: string, password: string) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      credentials: 'include', // Important for cookies
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (response.ok) {
      const data = await response.json();
      this.csrfToken = data.data.csrfToken;
      return data.data;
    }
    throw new Error('Login failed');
  }

  async makeApiCall(endpoint: string, options = {}) {
    if (!this.csrfToken) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(`${this.baseUrl}/api/proxy${endpoint}`, {
      ...options,
      credentials: 'include',
      headers: {
        ...options.headers,
        'X-CSRF-Token': this.csrfToken,
        'Content-Type': 'application/json'
      }
    });

    if (response.status === 401) {
      // Session expired, need to login again
      this.csrfToken = null;
      throw new Error('Session expired');
    }

    return response;
  }

  async logout() {
    if (!this.csrfToken) return;

    await fetch(`${this.baseUrl}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRF-Token': this.csrfToken,
        'Content-Type': 'application/json'
      }
    });

    this.csrfToken = null;
  }
}
```

## Common Issues and Solutions

### Issue: 401 Unauthorized
- **Cause**: Session expired or invalid
- **Solution**: Login again to get new session

### Issue: 403 Forbidden  
- **Cause**: Missing or invalid CSRF token
- **Solution**: Include X-CSRF-Token header with token from login

### Issue: 500 Internal Server Error
- **Cause**: Backend service error or database connection issue
- **Solution**: Check Azure Function logs

### Issue: CORS errors in browser
- **Cause**: Cross-origin requests blocked
- **Solution**: Ensure `credentials: 'include'` is set in fetch options

## Security Notes

1. **Never expose** the real API keys (they're now safely server-side)
2. **Always use HTTPS** for all requests
3. **Session cookies** are httpOnly and cannot be accessed via JavaScript
4. **CSRF tokens** prevent cross-site request forgery
5. **Sessions expire** after 60 minutes of inactivity

## Test Credentials

Default test user:
- Username: `tanmais`
- Password: `Login123#`

To create additional users, use the `setup-users.js` script in the azure-auth-gateway folder.