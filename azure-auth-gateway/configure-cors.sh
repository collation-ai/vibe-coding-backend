#!/bin/bash

# Configure CORS for Azure Function App to allow Lovable.dev and Lovable.app

FUNCTION_APP_NAME="vibe-auth-gateway"
RESOURCE_GROUP="DefaultResourceGroup-CUS"

echo "Configuring CORS for $FUNCTION_APP_NAME..."

# Add Lovable domains to CORS allowed origins
az functionapp cors add \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP_NAME \
  --allowed-origins \
    "https://*.lovable.dev" \
    "https://*.lovable.app" \
    "http://localhost:3000" \
    "http://localhost:8000"

# Show current CORS settings
echo ""
echo "Current CORS settings:"
az functionapp cors show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP_NAME

echo ""
echo "✅ CORS configuration complete!"
