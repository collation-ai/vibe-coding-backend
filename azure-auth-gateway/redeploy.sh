#!/bin/bash

# Azure Functions Re-deployment Script

echo "=== Redeploying Vibe Auth Gateway ==="
echo ""

# Configuration
RESOURCE_GROUP="vibe-coding"
FUNCTION_APP_NAME="vibe-auth-gateway"

cd /home/tanmais/vibe-coding-backend/azure-auth-gateway

# Check if func tools are installed
if ! command -v func &> /dev/null; then
    echo "Installing Azure Functions Core Tools..."
    npm install -g azure-functions-core-tools@4 --unsafe-perm true
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Check current settings
echo ""
echo "Checking current configuration..."
az functionapp config appsettings list \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --output table | grep -E "MASTER_DB_URL|VIBE_BACKEND_URL|VIBE_REAL_API_KEY|AZURE_STORAGE" || echo "Settings need configuration"

# Deploy using zip deployment
echo ""
echo "Creating deployment package..."

# Create a temporary copy without local.settings.json
mkdir -p temp_deploy
cp -r login logout proxy docs shared *.js *.json node_modules temp_deploy/ 2>/dev/null || true
rm -f temp_deploy/local.settings.json

# Create zip file
cd temp_deploy
zip -r ../deploy.zip . -x "local.settings.json" "test-*.js" "setup-*.js" "check-user.js"
cd ..

# Deploy to Azure
echo "Deploying to Azure Functions..."
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --src deploy.zip

# Clean up
rm -rf temp_deploy
rm -f deploy.zip

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Testing endpoints..."
sleep 10

# Test the login endpoint
echo "Testing login endpoint..."
curl -X POST "https://$FUNCTION_APP_NAME.azurewebsites.net/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}' \
    -w "\nHTTP Status: %{http_code}\n" \
    -s

echo ""
echo "If you see 404 errors, the app settings may need to be configured."
echo "Run: az functionapp config appsettings set --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --settings KEY=VALUE"