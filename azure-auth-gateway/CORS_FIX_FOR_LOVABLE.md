# CORS Fix for Lovable.dev Integration

## Problem
CORS error when trying to authenticate from Lovable.dev preview apps:
```
Access to fetch at 'https://vibe-auth-gateway.azurewebsites.net/api/auth/login' from origin 'https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app' has been blocked by CORS policy
```

## Root Cause
Azure Function Apps require CORS to be configured at **two levels**:
1. ✅ **Application Level** (in code) - Already done in `shared/cors.js`
2. ❌ **Platform Level** (Azure Portal/CLI) - **MISSING**

## Solution

### Option 1: Azure Portal (Recommended)

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Function App** → `vibe-auth-gateway`
3. In the left menu, under **API**, click **CORS**
4. Add the following allowed origins:
   ```
   https://lovable.dev
   https://lovable.app
   https://id-preview.lovable.app
   https://gptengineer.app
   http://localhost:3000
   http://localhost:8000
   ```
5. **Important**: Check the box for **"Enable Access-Control-Allow-Credentials"**
6. Click **Save**

### Option 2: Azure CLI

Run this command:

```bash
# Add Lovable domains
az functionapp cors add \
  --resource-group DefaultResourceGroup-CUS \
  --name vibe-auth-gateway \
  --allowed-origins \
    "https://lovable.dev" \
    "https://lovable.app" \
    "https://id-preview.lovable.app" \
    "https://gptengineer.app" \
    "http://localhost:3000" \
    "http://localhost:8000"

# Enable credentials
az functionapp config appsettings set \
  --resource-group DefaultResourceGroup-CUS \
  --name vibe-auth-gateway \
  --settings CORS_SUPPORT_CREDENTIALS=true
```

### Option 3: Using Azure Resource Manager

If you need wildcard support (*.lovable.app), you'll need to use ARM template or disable CORS in Azure and handle it entirely in code.

To disable Azure CORS and use application-level only:

```bash
az functionapp cors remove \
  --resource-group DefaultResourceGroup-CUS \
  --name vibe-auth-gateway \
  --allowed-origins "*"
```

## Code Changes Already Made

The following headers are now included in `shared/cors.js`:

```javascript
'Access-Control-Allow-Origin': origin,  // Dynamic based on request
'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Session-Id, X-Database-Name, X-API-Key, Authorization',
'Access-Control-Allow-Credentials': 'true',
'Access-Control-Expose-Headers': 'X-Session-Id, X-CSRF-Token'
```

## Verification

After configuring CORS, test with:

```bash
curl -X OPTIONS https://vibe-auth-gateway.azurewebsites.net/api/auth/login \
  -H "Origin: https://id-preview.lovable.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

You should see these headers in the response:
```
Access-Control-Allow-Origin: https://id-preview.lovable.app
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
Access-Control-Allow-Headers: Content-Type, X-CSRF-Token, X-Session-Id, X-Database-Name, X-API-Key, Authorization
Access-Control-Allow-Credentials: true
```

## Why This Happens

Azure Function Apps have a **platform-level CORS filter** that runs **before** your code. If a request doesn't pass the platform CORS check, it never reaches your function code. This is why even though our code has correct CORS headers, the OPTIONS request fails.

## Recommended Approach

**Use Azure Portal CORS** with specific domains. This is the most reliable approach for production.

For development/testing with many subdomains, you can:
1. Disable Azure platform CORS
2. Rely entirely on application-level CORS in `shared/cors.js`

To disable platform CORS:
```bash
az functionapp config cors clear \
  --resource-group DefaultResourceGroup-CUS \
  --name vibe-auth-gateway
```

Then ensure your function returns CORS headers for **ALL** responses, including errors.
