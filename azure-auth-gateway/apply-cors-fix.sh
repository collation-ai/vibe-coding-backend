#!/bin/bash

echo "Applying CORS fix to Azure Functions..."

# Backup original files
cp proxy/index.js proxy/index.js.backup
cp login/index.js login/index.js.backup
cp logout/index.js logout/index.js.backup

# Create shared CORS handler
cat > shared/cors.js << 'EOF'
// Allowed origins configuration
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS 
    ? process.env.ALLOWED_ORIGINS.split(',') 
    : [
        'http://localhost:8080',
        'http://localhost:8081', 
        'https://freshwater.azurestaticapps.net'
    ];

function getCorsOrigin(requestOrigin) {
    if (!requestOrigin) return ALLOWED_ORIGINS[0];
    
    // Check exact match
    if (ALLOWED_ORIGINS.includes(requestOrigin)) {
        return requestOrigin;
    }
    
    // Check if it's a preview environment
    if (requestOrigin.includes('freshwater') && requestOrigin.includes('.azurestaticapps.net')) {
        return requestOrigin;
    }
    
    return ALLOWED_ORIGINS[0];
}

function setCorsHeaders(context, req) {
    const requestOrigin = req.headers.origin || req.headers.referer;
    const corsOrigin = getCorsOrigin(requestOrigin);
    
    return {
        'Access-Control-Allow-Origin': corsOrigin,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Database-Name'
    };
}

module.exports = { getCorsOrigin, setCorsHeaders };
EOF

echo "Created shared/cors.js"

# Now update each function to use the shared CORS handler
echo "Updating proxy/index.js..."
# This would need the full file update - keeping original for now

echo "Updating login/index.js..."  
# This would need the full file update - keeping original for now

echo "Updating logout/index.js..."
# This would need the full file update - keeping original for now

echo ""
echo "CORS fix files prepared!"
echo ""
echo "Next steps:"
echo "1. Manually update the function files to use the shared CORS handler"
echo "2. Test locally: func start"
echo "3. Deploy to Azure:"
echo "   zip -r deploy.zip . -x '*.git*' -x 'node_modules/*' -x 'local.settings.json'"
echo "   az functionapp deployment source config-zip \\"
echo "     --resource-group vibe-coding \\"
echo "     --name vibe-auth-gateway \\"
echo "     --src deploy.zip"
echo ""
echo "4. Set environment variable for allowed origins:"
echo "   az functionapp config appsettings set \\"
echo "     --resource-group vibe-coding \\"
echo "     --name vibe-auth-gateway \\"
echo "     --settings 'ALLOWED_ORIGINS=https://freshwater.azurestaticapps.net,http://localhost:8080,http://localhost:8081'"