#!/bin/bash

# Quick CORS fix for Azure Function App
# This disables platform-level CORS and lets our code handle it

FUNCTION_APP_NAME="vibe-auth-gateway"
RESOURCE_GROUP="DefaultResourceGroup-CUS"

echo "🔧 Fixing CORS for Lovable.dev integration..."
echo ""

echo "Option 1: Clear Azure platform CORS (recommended for wildcard subdomain support)"
echo "This will let our application code (shared/cors.js) handle ALL CORS requests"
echo ""
read -p "Clear Azure platform CORS? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Clearing platform CORS..."
    az functionapp cors remove \
      --resource-group $RESOURCE_GROUP \
      --name $FUNCTION_APP_NAME \
      --allowed-origins "*"

    echo "✅ Platform CORS cleared. Application will handle CORS."
fi

echo ""
echo "Option 2: Add specific Lovable domains to platform CORS"
echo ""
read -p "Add Lovable domains to platform CORS? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Adding Lovable domains..."
    az functionapp cors add \
      --resource-group $RESOURCE_GROUP \
      --name $FUNCTION_APP_NAME \
      --allowed-origins \
        "https://lovable.dev" \
        "https://lovable.app" \
        "https://id-preview.lovable.app" \
        "http://localhost:3000"

    echo "✅ Lovable domains added to platform CORS"
fi

echo ""
echo "Current CORS settings:"
az functionapp cors show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP_NAME

echo ""
echo "✅ Done! Please test your Lovable.dev app again."
