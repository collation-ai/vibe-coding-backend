# Emergency CORS Fix for Azure Functions

## The Problem
The Functions app is not properly setting `Access-Control-Allow-Credentials: true`

## Quick Fix Instructions

### 1. Update login/index.js

Find this section in `/home/tanmais/vibe-coding-backend/azure-auth-gateway/login/index.js`:

```javascript
// Set CORS headers
context.res = {
    headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'
    }
};
```

Replace with:

```javascript
// Set CORS headers - FIXED VERSION
const allowedOrigin = 'https://lemon-mud-0cbacb00f.1.azurestaticapps.net';
context.res = {
    headers: {
        'Access-Control-Allow-Origin': allowedOrigin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true'  // MUST be string 'true'
    }
};
```

### 2. Update proxy/index.js

Similarly update the CORS headers section to use specific origin:

```javascript
// Set CORS headers - FIXED VERSION
const allowedOrigin = 'https://lemon-mud-0cbacb00f.1.azurestaticapps.net';
context.res = {
    headers: {
        'Access-Control-Allow-Origin': allowedOrigin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Database-Name',
        'Access-Control-Allow-Credentials': 'true'  // MUST be string 'true'
    }
};
```

### 3. Deploy the Fix

```bash
cd ~/vibe-coding-backend/azure-auth-gateway

# Create deployment package
zip -r deploy-fix.zip . -x "*.git*" -x "node_modules/*" -x "local.settings.json"

# Deploy to Azure
az functionapp deployment source config-zip \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --src deploy-fix.zip

# Wait 2-3 minutes for deployment to complete
```

## Test the Fix

After deployment:
1. Clear browser cache/cookies
2. Try logging in again
3. Check Network tab - the login response should have:
   - `Access-Control-Allow-Origin: https://lemon-mud-0cbacb00f.1.azurestaticapps.net`
   - `Access-Control-Allow-Credentials: true`

## If Still Not Working

The Functions runtime might be overriding headers. In that case, add this to your `host.json`:

```json
{
  "version": "2.0",
  "extensions": {
    "http": {
      "cors": {
        "allowedOrigins": [
          "https://lemon-mud-0cbacb00f.1.azurestaticapps.net"
        ],
        "supportCredentials": true
      }
    }
  }
}
```

Then redeploy.