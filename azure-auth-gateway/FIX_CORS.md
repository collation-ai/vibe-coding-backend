# Fix CORS Configuration for Azure Auth Gateway

## Problem
The current Azure Functions app uses `Access-Control-Allow-Origin: '*'` with `Access-Control-Allow-Credentials: 'true'`, which is invalid according to CORS specification. When credentials (cookies) are included, the origin must be specific, not a wildcard.

## Quick Fix (Update Functions Code)

### 1. Update the proxy function

Replace `/home/tanmais/vibe-coding-backend/azure-auth-gateway/proxy/index.js` with the fixed version:

```javascript
// At the top of the file, add allowed origins configuration
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS 
    ? process.env.ALLOWED_ORIGINS.split(',') 
    : [
        'http://localhost:8080',
        'http://localhost:8081',
        'https://lemon-mud-0cbacb00f.1.azurestaticapps.net'
    ];

function getCorsOrigin(requestOrigin) {
    if (!requestOrigin) return ALLOWED_ORIGINS[0];
    return ALLOWED_ORIGINS.includes(requestOrigin) ? requestOrigin : ALLOWED_ORIGINS[0];
}

// In the function handler, replace the CORS headers section:
const requestOrigin = req.headers.origin || req.headers.referer;
const corsOrigin = getCorsOrigin(requestOrigin);

context.res = {
    headers: {
        'Access-Control-Allow-Origin': corsOrigin,  // Specific origin instead of '*'
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Database-Name',
        'Access-Control-Allow-Credentials': 'true'
    }
};
```

### 2. Update the login function

Similarly update `/home/tanmais/vibe-coding-backend/azure-auth-gateway/login/index.js`:

```javascript
// Add the same ALLOWED_ORIGINS and getCorsOrigin function

// Replace the CORS headers section:
const requestOrigin = req.headers.origin || req.headers.referer;
const corsOrigin = getCorsOrigin(requestOrigin);

context.res = {
    headers: {
        'Access-Control-Allow-Origin': corsOrigin,  // Specific origin instead of '*'
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true',
        'Set-Cookie': `vibe_session=${sessionId}; HttpOnly; Secure; SameSite=None; Path=/; Max-Age=3600`
    }
};
```

### 3. Update the logout function

Do the same for `/home/tanmais/vibe-coding-backend/azure-auth-gateway/logout/index.js`.

## Deploy the Fix

### Option 1: Quick Deploy via Azure CLI

```bash
# Navigate to the azure-auth-gateway directory
cd ~/vibe-coding-backend/azure-auth-gateway

# Create a deployment package
zip -r deploy.zip . -x "*.git*" -x "node_modules/*" -x "local.settings.json"

# Deploy to Azure Functions
az functionapp deployment source config-zip \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --src deploy.zip
```

### Option 2: Set Application Settings for Allowed Origins

```bash
# Set allowed origins as an environment variable
az functionapp config appsettings set \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --settings "ALLOWED_ORIGINS=https://lemon-mud-0cbacb00f.1.azurestaticapps.net,http://localhost:8080,http://localhost:8081"
```

## Important Cookie Configuration

For cross-origin cookies to work properly, ensure cookies are set with:
- `SameSite=None` - Required for cross-origin cookies
- `Secure` - Required when using SameSite=None
- `HttpOnly` - For security
- `Path=/` - To ensure cookie is sent with all requests

## Test the Fix

1. Deploy the changes
2. Clear browser cookies/cache
3. Try logging in from your Static Web App
4. Check browser DevTools:
   - Network tab: Verify CORS headers show your specific origin
   - Application tab: Verify session cookie is set
   - Console: Check for any CORS errors

## Alternative: Use Azure API Management

For production, consider using Azure API Management in front of your Functions app for better CORS control and API governance.

## Troubleshooting

If cookies still aren't working:

1. **Check Cookie Domain**: Cookies set on `*.azurewebsites.net` should work across subdomains
2. **Verify HTTPS**: Both sites must use HTTPS for Secure cookies
3. **Browser Settings**: Some browsers block third-party cookies by default
4. **Test with curl**: 
   ```bash
   curl -v https://vibe-auth-gateway.azurewebsites.net/api/auth/login \
     -H "Origin: https://freshwater.azurestaticapps.net" \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
   ```
   Check the `Access-Control-Allow-Origin` header in the response.