const openApiSpec = require('../openapi.json');

module.exports = async function (context, req) {
    context.log('Docs endpoint called');
    
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vibe Coding Gateway API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body { margin: 0; padding: 0; }
        .swagger-ui .topbar { display: none; }
        .info { margin: 20px; padding: 20px; background: #f0f0f0; border-radius: 8px; }
        .info h2 { color: #333; }
        .info .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .info .success { background: #d4edda; border: 1px solid #28a745; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .info code { background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="info">
        <h2>🔒 Vibe Coding Authentication Gateway API</h2>

        <p>
            This gateway provides secure, session-based authentication for the Vibe Coding Backend.
            All authentication is handled server-side with httpOnly cookies and CSRF tokens.
        </p>

        <h3>Authentication Flow:</h3>
        <ol>
            <li><strong>Login:</strong> Call <code>/api/auth/login</code> with username, password, and database name</li>
            <li><strong>Receive Credentials:</strong>
                <ul>
                    <li>Session ID is set as an httpOnly cookie (secure, not accessible via JavaScript)</li>
                    <li>CSRF token is returned in the response body</li>
                </ul>
            </li>
            <li><strong>Make API Calls:</strong> Include both the session cookie and CSRF token in all subsequent requests</li>
            <li><strong>Logout:</strong> Call <code>/api/auth/logout</code> to invalidate the session</li>
        </ol>

        <div class="warning">
            <strong>⚠️ Important Note:</strong> The session cookie is set with the <code>httpOnly</code> flag,
            which means it's not visible in JavaScript or Swagger UI. To view it:
            <ul>
                <li>Open browser DevTools (F12) → Network tab → Check response headers for <code>set-cookie</code></li>
                <li>Use <code>curl -i</code> to see all response headers including cookies</li>
            </ul>
        </div>

        <h3>Example Credentials (Replace with Your Own):</h3>
        <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #ddd;">
Username: your_username
Password: your_password
Database: your_database_name
        </pre>

        <h3>Complete Working Examples:</h3>
        <pre style="background: #2d2d2d; color: #ccc; padding: 15px; border-radius: 5px; overflow-x: auto;">
# ============================================================
# STEP 1: Login and get session cookie + CSRF token
# ============================================================
curl -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "your_username",
    "password": "your_password",
    "database": "your_database_name"
  }'

# Response includes:
# Header: set-cookie: vibe_session=abc123-def456-ghi789; httponly; secure; ...
# Body: {
#   "success": true,
#   "data": {
#     "csrfToken": "xyz789-uvw456-rst123",
#     "username": "your_username",
#     "email": "your_email@example.com",
#     "database": "your_database_name",
#     "expiresIn": 3600
#   }
# }

# ============================================================
# STEP 2: Get user permissions
# ============================================================
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/auth/permissions" \\
  -H "Cookie: vibe_session=abc123-def456-ghi789" \\
  -H "X-CSRF-Token: xyz789-uvw456-rst123"

# Response:
# {
#   "success": true,
#   "data": {
#     "databases": ["your_database_name"],
#     "permissions": [
#       {
#         "database": "your_database_name",
#         "schema": "public",
#         "permission": "read_write"
#       }
#     ]
#   }
# }

# ============================================================
# STEP 3: Execute a SQL query
# ============================================================
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query" \\
  -H "Content-Type: application/json" \\
  -H "Cookie: vibe_session=abc123-def456-ghi789" \\
  -H "X-CSRF-Token: xyz789-uvw456-rst123" \\
  -d '{
    "database": "your_database_name",
    "query": "SELECT * FROM users LIMIT 10",
    "params": []
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "rows": [...],
#     "affected_rows": 10
#   },
#   "metadata": {
#     "database": "your_database_name",
#     "execution_time_ms": 45
#   }
# }

# ============================================================
# STEP 4: Execute a parameterized query (safer)
# ============================================================
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query" \\
  -H "Content-Type: application/json" \\
  -H "Cookie: vibe_session=abc123-def456-ghi789" \\
  -H "X-CSRF-Token: xyz789-uvw456-rst123" \\
  -d '{
    "database": "your_database_name",
    "query": "SELECT * FROM users WHERE email = $1",
    "params": ["user@example.com"]
  }'

# ============================================================
# STEP 5: Insert data
# ============================================================
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query" \\
  -H "Content-Type: application/json" \\
  -H "Cookie: vibe_session=abc123-def456-ghi789" \\
  -H "X-CSRF-Token: xyz789-uvw456-rst123" \\
  -d '{
    "database": "your_database_name",
    "query": "INSERT INTO users (email, username) VALUES ($1, $2) RETURNING *",
    "params": ["newuser@example.com", "newuser"]
  }'

# ============================================================
# STEP 6: Logout when done
# ============================================================
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/logout" \\
  -H "Cookie: vibe_session=abc123-def456-ghi789" \\
  -H "X-CSRF-Token: xyz789-uvw456-rst123"

# Response:
# {
#   "success": true,
#   "message": "Logged out successfully"
# }
        </pre>

        <h3>Security Features:</h3>
        <ul>
            <li><strong>HttpOnly Cookies:</strong> Session tokens cannot be accessed by JavaScript</li>
            <li><strong>CSRF Protection:</strong> All state-changing requests require CSRF token</li>
            <li><strong>Secure Flag:</strong> Cookies only transmitted over HTTPS</li>
            <li><strong>SameSite Protection:</strong> Configured for cross-origin requests</li>
            <li><strong>Session Expiry:</strong> Sessions automatically expire after inactivity</li>
        </ul>
    </div>
    
    <div id="swagger-ui"></div>
    
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        const spec = ${JSON.stringify(openApiSpec)};
        
        window.onload = function() {
            const ui = SwaggerUIBundle({
                spec: spec,
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
        }
    </script>
</body>
</html>`;
    
    context.res = {
        status: 200,
        headers: {
            'Content-Type': 'text/html'
        },
        body: html
    };
};