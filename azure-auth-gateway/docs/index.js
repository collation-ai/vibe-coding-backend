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
        
        <div class="success">
            <strong>✅ Security Issue Resolved:</strong> API keys are no longer exposed in the browser. 
            All authentication is handled server-side through secure sessions.
        </div>
        
        <h3>Quick Start:</h3>
        <ol>
            <li><strong>Login:</strong> Use <code>/api/auth/login</code> with your username and password</li>
            <li><strong>Get Session & CSRF:</strong> 
                <ul>
                    <li>Session ID comes in the <code>Set-Cookie</code> header (⚠️ NOT visible in Swagger UI)</li>
                    <li>CSRF token comes in the JSON response body</li>
                </ul>
            </li>
            <li><strong>Make API Calls:</strong> Include both session cookie and CSRF token in all requests</li>
        </ol>
        
        <div class="warning">
            <strong>⚠️ Important for Testing:</strong> Swagger UI doesn't show the <code>Set-Cookie</code> header. 
            To get the session cookie, you need to:
            <ol>
                <li>Open browser DevTools (F12) → Network tab</li>
                <li>Execute the login request</li>
                <li>Find the login request and check Response Headers for <code>set-cookie: vibe_session=xxxxx</code></li>
                <li>Or use curl: <code>curl -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" -H "Content-Type: application/json" -d '{"username":"tanmais","password":"Login123#"}'</code></li>
            </ol>
        </div>
        
        <h3>Test Credentials:</h3>
        <ul>
            <li>Username: <code>tanmais</code></li>
            <li>Password: <code>Login123#</code></li>
        </ul>
        
        <h3>Complete Working Example:</h3>
        <pre style="background: #2d2d2d; color: #ccc; padding: 15px; border-radius: 5px; overflow-x: auto;">
# 1. Login and get BOTH session cookie AND CSRF token
curl -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username":"tanmais","password":"Login123#"}'

# Response will include:
# Header: set-cookie: vibe_session=fa0f2c81-2208-4446-b988-fa7c0a956f65; ...
# Body: {"data":{"csrfToken":"6136ca40-fcab-475b-9df3-45f87321b26a",...}}

# 2. Use BOTH values in subsequent requests
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/auth/permissions" \\
  -H "Cookie: vibe_session=fa0f2c81-2208-4446-b988-fa7c0a956f65" \\
  -H "X-CSRF-Token: 6136ca40-fcab-475b-9df3-45f87321b26a"
        </pre>
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