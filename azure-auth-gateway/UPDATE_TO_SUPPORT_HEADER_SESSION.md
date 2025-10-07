# Update Azure Functions to Accept Session ID from Headers

Since cross-site cookies aren't working, we need to update the Functions to accept session ID from headers as an alternative.

## Update proxy/index.js

Find this line:
```javascript
const sessionId = cookies.vibe_session;
```

Replace with:
```javascript
// Accept session from either cookie OR header (for cross-site scenarios)
const sessionId = cookies.vibe_session || req.headers['x-session-id'];
```

## Full Updated Section

In `/home/tanmais/vibe-coding-backend/azure-auth-gateway/proxy/index.js`:

```javascript
// Around line 28-30, update to:
// Get session from cookie OR header
const cookies = parseCookies(req.headers.cookie || '');
const sessionId = cookies.vibe_session || req.headers['x-session-id'];
const csrfToken = req.headers['x-csrf-token'];

context.log('Session ID source:', cookies.vibe_session ? 'cookie' : req.headers['x-session-id'] ? 'header' : 'none');
```

## Also Update login/index.js

Make the login endpoint return the session ID in the response body:

```javascript
// After creating the session (around line 60-70), add sessionId to response:
context.res.body = {
    success: true,
    data: {
        csrfToken: csrfToken,
        sessionId: sessionId,  // ADD THIS LINE
        username: user.username,
        email: user.email,
        expiresIn: 3600
    }
};
```

## Deploy the Updates

```bash
cd ~/vibe-coding-backend/azure-auth-gateway

# Deploy to Azure
zip -r deploy-session-fix.zip . -x "*.git*" -x "node_modules/*" -x "local.settings.json"

az functionapp deployment source config-zip \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --src deploy-session-fix.zip
```

## How It Works

1. **Login**: Returns session ID in response body
2. **Frontend**: Stores session ID in localStorage 
3. **API Calls**: Sends session ID in `X-Session-Id` header
4. **Backend**: Accepts session from either cookie OR header

This bypasses the cross-site cookie restriction while maintaining security through CSRF tokens.