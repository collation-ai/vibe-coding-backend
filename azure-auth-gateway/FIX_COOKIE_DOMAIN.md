# Fix Cookie Domain Issue

## Problem
The session cookie is being set but not sent with subsequent requests because:
- Cookie is set for `vibe-auth-gateway.azurewebsites.net`
- Requests are cross-site from `lemon-mud-0cbacb00f.1.azurestaticapps.net`
- Even with `SameSite=None` and `credentials: 'include'`, some browsers have issues

## Solution 1: Update Cookie Domain (Recommended)

Update the login function to set cookie with explicit domain:

### In login/index.js

Find where the cookie is set and update:

```javascript
// After successful login, when setting the session cookie:
const cookieOptions = [
    `vibe_session=${sessionId}`,
    'HttpOnly',
    'Secure',
    'SameSite=None',
    'Path=/',
    'Max-Age=3600',
    // Add explicit domain for broader compatibility
    'Domain=.azurewebsites.net'  // This allows cookie to work across all *.azurewebsites.net subdomains
];

context.res.headers['Set-Cookie'] = cookieOptions.join('; ');
```

## Solution 2: Check Browser Settings

Some browsers block third-party cookies by default:

### Chrome
1. Go to Settings → Privacy and security → Cookies
2. Check if "Block third-party cookies" is enabled
3. Add exception for `[*.]azurewebsites.net`

### Edge/Firefox
Similar settings in privacy section

## Solution 3: Use a Proxy/Rewrite Rule

Configure Azure Static Web Apps to proxy API calls:

### Add to staticwebapp.config.json:

```json
{
  "routes": [
    {
      "route": "/api/*",
      "rewrite": "https://vibe-auth-gateway.azurewebsites.net/api/*"
    },
    {
      "route": "/*",
      "serve": "/index.html",
      "statusCode": 200
    }
  ],
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/images/*.{png,jpg,gif}", "/css/*"]
  }
}
```

Then update the frontend to use relative URLs:

```javascript
// In api.ts
export const API_BASE_URL = ''; // Empty for both dev and prod
```

## Solution 4: Alternative - Use Authorization Header

Instead of relying on cookies, pass the session ID in headers:

### Frontend (api.ts):
```javascript
private getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  };
  
  if (this.csrfToken) {
    headers['X-CSRF-Token'] = this.csrfToken;
  }
  
  if (this.sessionId) {
    headers['X-Session-Id'] = this.sessionId;  // Pass session in header instead of cookie
  }
  
  return headers;
}
```

### Backend (proxy/index.js):
```javascript
// Get session from either cookie OR header
const cookies = parseCookies(req.headers.cookie || '');
const sessionId = cookies.vibe_session || req.headers['x-session-id'];
```

## Immediate Test

To verify if it's a cookie issue, open browser console and run:

```javascript
// Before making an API call, manually check:
fetch('https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': 'YOUR_CSRF_TOKEN_HERE'
  },
  body: JSON.stringify({
    database: 'cdb_written_976_poetry',
    query: 'SELECT 1',
    params: []
  })
}).then(r => r.json()).then(console.log);
```

Check Network tab to see if Cookie header is sent.