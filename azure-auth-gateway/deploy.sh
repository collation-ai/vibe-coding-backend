#!/bin/bash

# Azure Functions Deployment Script for Vibe Auth Gateway

echo "=== Deploying Vibe Auth Gateway to Azure ==="
echo ""

# Configuration
RESOURCE_GROUP="vibe-coding"
FUNCTION_APP_NAME="vibe-auth-gateway"
STORAGE_ACCOUNT="vibeauthstorage"
LOCATION="eastus"
RUNTIME="node"
RUNTIME_VERSION="18"

# Check if logged in to Azure
echo "Checking Azure login status..."
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Please login to Azure first:"
    az login
fi

# Create Storage Account if it doesn't exist
echo "Creating storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --sku Standard_LRS \
    --kind StorageV2 \
    2>/dev/null

# Create Function App
echo "Creating Function App..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime $RUNTIME \
    --runtime-version $RUNTIME_VERSION \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_ACCOUNT \
    --os-type Linux

# Configure CORS
echo "Configuring CORS..."
az functionapp cors add \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --allowed-origins "*"

# Set app settings
echo "Configuring application settings..."
echo "Please provide the following configuration values:"
echo ""
read -p "Master Database URL: " MASTER_DB_URL
read -p "Vibe Backend URL (e.g., https://vibe-coding-backend.azurewebsites.net): " VIBE_BACKEND_URL
read -p "Vibe Real API Key: " VIBE_REAL_API_KEY
read -p "Azure Storage Connection String: " AZURE_STORAGE_CONNECTION
read -p "JWT Secret (generate a random string): " JWT_SECRET

# Apply settings
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
    "MASTER_DB_URL=$MASTER_DB_URL" \
    "VIBE_BACKEND_URL=$VIBE_BACKEND_URL" \
    "VIBE_REAL_API_KEY=$VIBE_REAL_API_KEY" \
    "AZURE_STORAGE_CONNECTION=$AZURE_STORAGE_CONNECTION" \
    "JWT_SECRET=$JWT_SECRET" \
    "SESSION_TIMEOUT_MINUTES=60"

# Install dependencies
echo "Installing dependencies..."
npm install

# Deploy the function app
echo "Deploying function app..."
func azure functionapp publish $FUNCTION_APP_NAME --javascript

# Get the function URL
echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Your auth gateway is available at:"
echo "https://$FUNCTION_APP_NAME.azurewebsites.net"
echo ""
echo "Endpoints:"
echo "- Login: https://$FUNCTION_APP_NAME.azurewebsites.net/api/auth/login"
echo "- Logout: https://$FUNCTION_APP_NAME.azurewebsites.net/api/auth/logout"
echo "- Proxy: https://$FUNCTION_APP_NAME.azurewebsites.net/api/proxy/*"
echo ""
echo "Next steps:"
echo "1. Run database-setup.sql on your master database"
echo "2. Create users using: node setup-users.js"
echo "3. Update Lovable app to use the new auth gateway"