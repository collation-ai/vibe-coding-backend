#!/bin/bash

echo "Configuring Azure Function App Settings..."

# Set all required environment variables
az functionapp config appsettings set \
  --name vibe-auth-gateway \
  --resource-group vibe-coding \
  --settings \
    MASTER_DB_URL="postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require" \
    VIBE_BACKEND_URL="https://vibe-coding-backend.azurewebsites.net" \
    VIBE_REAL_API_KEY="vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \
    SESSION_TIMEOUT_MINUTES="60" \
    JWT_SECRET="vibe-secret-jwt-key-2024-secure-random-string"

# For Azure Storage, we need to create a storage account first or use existing
az storage account show --name vibeauthstorage --resource-group vibe-coding &>/dev/null
if [ $? -ne 0 ]; then
    echo "Creating storage account..."
    az storage account create \
      --name vibeauthstorage \
      --resource-group vibe-coding \
      --location eastus \
      --sku Standard_LRS
fi

# Get the storage connection string
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --name vibeauthstorage \
  --resource-group vibe-coding \
  --query connectionString \
  --output tsv)

if [ -n "$STORAGE_CONNECTION" ]; then
    echo "Setting storage connection..."
    az functionapp config appsettings set \
      --name vibe-auth-gateway \
      --resource-group vibe-coding \
      --settings AZURE_STORAGE_CONNECTION="$STORAGE_CONNECTION"
fi

echo "Configuration complete!"