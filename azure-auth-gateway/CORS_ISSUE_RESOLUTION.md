# CORS Issue Resolution - Azure Functions Authentication Gateway

## Problem Statement

After redeploying the Azure Functions authentication gateway to a new repository, CORS errors prevented authentication from Lovable.dev:

```
Access to fetch at 'https://vibe-auth-gateway.azurewebsites.net/api/auth/login'
from origin 'https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app'
has been blocked by CORS policy: Response to preflight request doesn't pass
access control check: No 'Access-Control-Allow-Origin' header is present on
the requested resource.
```

## Symptoms

1. **OPTIONS (preflight) requests** returned HTTP 204 with **no CORS headers**
2. **POST requests** worked correctly with all proper CORS headers
3. The setup had been working in the previous repository deployment

## Root Cause

Azure Functions has two levels of CORS configuration:

1. **Platform-level CORS** (configured via Azure CLI/Portal)
2. **Application-level CORS** (configured in function code)

When platform CORS is enabled, Azure intercepts OPTIONS requests **at the infrastructure level** before they reach function code.

The issue was that **platform CORS was enabled but had an empty `allowedOrigins` list**:

```bash
az functionapp cors show --resource-group vibe-coding --name vibe-auth-gateway
# Result:
{
  "allowedOrigins": [],
  "supportCredentials": true
}
```

With an empty origins list, Azure was intercepting OPTIONS requests but not adding any CORS headers to the response.

## Solution

Re-add the Lovable origins to Azure platform CORS configuration:

```bash
az functionapp cors add \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --allowed-origins \
    "https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app" \
    "https://*.lovable.dev" \
    "https://*.lovable.app"
```

### Verification

After adding origins, verify the configuration:

```bash
az functionapp cors show --resource-group vibe-coding --name vibe-auth-gateway
```

Expected output:
```json
{
  "allowedOrigins": [
    "https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app",
    "https://*.lovable.dev",
    "https://*.lovable.app"
  ],
  "supportCredentials": true
}
```

### Test OPTIONS Request

```bash
curl -X OPTIONS "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Origin: https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-csrf-token" \
  -i
```

Expected response headers:
```
HTTP/2 204
access-control-allow-origin: https://id-preview--c2df6998-b552-43e6-8cee-4a320be80e25.lovable.app
access-control-allow-credentials: true
access-control-allow-methods: POST
access-control-allow-headers: content-type,x-csrf-token
vary: Origin
```

## How Azure Platform CORS Works

### Preflight (OPTIONS) Requests
- Intercepted by Azure infrastructure **before** reaching function code
- Azure automatically echoes back headers listed in `Access-Control-Request-Headers`
- Returns HTTP 204 with CORS headers from platform configuration

### Actual Requests (POST, GET, etc.)
- Reach function code normally
- Function code adds CORS headers via `getCorsHeaders()` in `shared/cors.js`
- Returns response with both platform and application CORS headers

## Key Files

### `/azure-auth-gateway/shared/cors.js`
Contains the `getCorsHeaders()` helper function that handles application-level CORS:

```javascript
function getCorsHeaders(req) {
    const origin = req.headers.origin || req.headers.Origin || '';

    if (origin && (origin.includes('lovable.dev') || origin.includes('lovable.app'))) {
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
            'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Session-Id, X-Database-Name, X-API-Key, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Expose-Headers': 'X-Session-Id, X-CSRF-Token'
        };
    }
    // ... fallback for other origins
}
```

### `/azure-auth-gateway/login/index.js`
Login endpoint that uses `getCorsHeaders()`:

```javascript
const { getCorsHeaders } = require('../shared/cors');

module.exports = async function (context, req) {
    const corsHeaders = getCorsHeaders(req);

    // Handle preflight (though platform CORS intercepts this)
    if (req.method === 'OPTIONS') {
        context.res = {
            status: 200,
            headers: corsHeaders,
            body: 'OK'
        };
        return;
    }

    // Set CORS headers for regular requests
    context.res = {
        headers: corsHeaders
    };

    // ... rest of login logic
}
```

## Troubleshooting New CORS Errors

If you encounter CORS errors from a new origin (e.g., a new Lovable project or deployment):

### Step 1: Identify the Actual Origin

The origin might not be what you expect, especially when using iframes or preview environments.

**How to find the actual origin:**

1. Open **Browser DevTools** (F12) in the application where the CORS error occurs
2. Go to the **Network** tab
3. Reproduce the failing request (e.g., try logging in)
4. Click on the failed request in the Network tab
5. Look at the **Request Headers** section
6. Find the **Referer** or **Origin** header - this shows the actual origin being sent

**Example:**
```
Referer: https://6607ed13-4a29-44a2-9c16-fbc4ed99b0de.lovableproject.com/
Origin: https://6607ed13-4a29-44a2-9c16-fbc4ed99b0de.lovableproject.com
```

### Step 2: Add the Specific Origin

Even if you have wildcards configured (like `https://*.lovableproject.com`), Azure's wildcard matching can be inconsistent. Add the specific origin:

```bash
az functionapp cors add \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --allowed-origins "https://6607ed13-4a29-44a2-9c16-fbc4ed99b0de.lovableproject.com"
```

### Step 3: Verify and Test

```bash
# Check configuration
az functionapp cors show --resource-group vibe-coding --name vibe-auth-gateway

# Test with curl
curl -X OPTIONS "https://vibe-auth-gateway.azurewebsites.net/api/login" \
  -H "Origin: https://6607ed13-4a29-44a2-9c16-fbc4ed99b0de.lovableproject.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-csrf-token" \
  -i
```

### Common Lovable Origins

Different Lovable environments use different origins:

- **Published apps**: `https://your-app-name.lovable.app`
- **Preview iframe**: `https://[project-id].lovableproject.com`
- **Preview domain**: `https://preview.lovable.dev` or `https://preview.lovable.app`
- **Editor domain**: `https://lovable.dev`

**Pro tip:** Always check the actual Referer/Origin header rather than guessing the URL format.

## Important Notes

1. **Platform CORS takes precedence for OPTIONS requests** - When platform CORS is enabled with origins, it intercepts OPTIONS before function code runs.

2. **Wildcards work in Azure platform CORS BUT may need explicit entries** - Patterns like `https://*.lovable.dev` should match all subdomains, but Azure's wildcard matching can be inconsistent. When in doubt, add the specific subdomain explicitly.

3. **supportCredentials must be true** - Required for cookies and authentication headers to work with CORS.

4. **No need to configure allowed headers explicitly** - Azure platform CORS automatically allows whatever headers the browser requests in `Access-Control-Request-Headers`.

5. **Function code CORS still matters** - Application-level CORS in function code handles actual POST/GET/etc. requests and provides more granular control.

6. **Check the Referer header in Network tab** - The easiest way to identify the correct origin when troubleshooting CORS issues is to look at the Referer or Origin header in the browser's Network tab (DevTools → Network → Click failed request → Request Headers).

## Why This Happened During Redeployment

When the Azure Function App was recreated in the new repository:
- The function code was deployed via CI/CD
- Environment variables were migrated
- **Platform CORS configuration was NOT automatically migrated**

Platform CORS is an infrastructure setting, not part of the code, so it must be reconfigured manually when creating a new Function App.

## Prevention for Future Deployments

To avoid this issue when deploying to a new environment:

1. **Document platform settings** - Keep a record of all `az` commands needed to configure the Function App
2. **Infrastructure as Code** - Use Azure Resource Manager (ARM) templates or Terraform to codify all settings
3. **Deployment checklist** - Include platform CORS configuration in deployment procedures
4. **Automated scripts** - Create setup scripts that configure both code and platform settings

## Alternative Approaches Considered

### 1. Disable Platform CORS Entirely
Attempted to disable platform CORS and handle all CORS in function code. However, Azure Functions v4 routing system still intercepts OPTIONS requests at the platform level even when platform CORS is disabled.

### 2. host.json CORS Configuration
Azure Functions v4 doesn't support CORS configuration in `host.json` (this was a v1/v2 feature).

### 3. Azure API Management
Could place API Management in front of Functions to handle CORS at the gateway level, but this adds complexity and cost.

## Conclusion

The CORS issue was resolved by properly configuring Azure platform CORS with the required origins. This is a **required infrastructure configuration** separate from the application code, and must be set up whenever deploying to a new Azure Function App.

The combination of platform CORS (for OPTIONS) and application CORS (for actual requests) provides robust cross-origin support for the authentication gateway.

---

**Date Resolved:** October 7, 2025
**Issue Duration:** Multiple deployments over several hours
**Resolution Time:** Immediate after identifying empty allowedOrigins list
