# 🚀 Azure App Service Deployment Guide

## Prerequisites
- Azure subscription with active account
- Azure CLI installed locally
- GitHub repository (already set up)
- Azure PostgreSQL database (already configured)

## Initial Setup (One-time)

### 1. Install Azure CLI
```bash
# macOS
brew update && brew install azure-cli

# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### 2. Login to Azure
```bash
az login
```

### 3. Create Resource Group (if needed)
```bash
# Create resource group
az group create --name vibe-coding-rg --location eastus
```

### 4. Create App Service Plan
```bash
# Create App Service plan (B1 is basic tier, good for starting)
az appservice plan create \
  --name vibe-coding-plan \
  --resource-group vibe-coding-rg \
  --sku B1 \
  --is-linux
```

### 5. Create Web App
```bash
# Create the web app
az webapp create \
  --resource-group vibe-coding-rg \
  --plan vibe-coding-plan \
  --name vibe-coding-backend \
  --runtime "PYTHON:3.11" \
  --startup-file "startup.sh"
```

### 6. Configure Environment Variables
```bash
# Set environment variables
az webapp config appsettings set \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --settings \
    MASTER_DB_URL="$MASTER_DB_URL" \
    AZURE_DB_HOST="$AZURE_DB_HOST" \
    ENCRYPTION_KEY="$ENCRYPTION_KEY" \
    API_KEY_SALT="$API_KEY_SALT" \
    WEBSITES_PORT="8000"
```

### 7. Enable Logging
```bash
# Enable application logging
az webapp log config \
  --name vibe-coding-backend \
  --resource-group vibe-coding-rg \
  --application-logging filesystem \
  --level verbose
```

## GitHub Actions Setup

### 1. Get Publish Profile
```bash
# Download publish profile
az webapp deployment list-publishing-profiles \
  --name vibe-coding-backend \
  --resource-group vibe-coding-rg \
  --xml > publish-profile.xml
```

### 2. Add to GitHub Secrets
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
4. Value: Copy entire content of `publish-profile.xml`
5. Click "Add secret"

### 3. Update Workflow
Edit `.github/workflows/azure-deploy.yml`:
- Change `AZURE_WEBAPP_NAME` to your app name

### 4. Deploy
Push to main branch:
```bash
git add .
git commit -m "Configure Azure deployment"
git push origin main
```

## Manual Deployment (Alternative)

### Using Azure CLI
```bash
# Deploy from local directory
az webapp up \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --runtime "PYTHON:3.11" \
  --sku B1
```

### Using ZIP Deploy
```bash
# Create deployment package
zip -r deploy.zip . -x "*.git*" -x "*.env" -x "tests/*" -x "scripts/*"

# Deploy
az webapp deployment source config-zip \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --src deploy.zip
```

## Monitoring & Maintenance

### View Logs
```bash
# Stream logs
az webapp log tail \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend

# Download logs
az webapp log download \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --log-file logs.zip
```

### Check Health
```bash
# Get app status
az webapp show \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --query state

# Test endpoint
curl https://vibe-coding-backend.azurewebsites.net/api/health
```

### Restart App
```bash
az webapp restart \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend
```

### Scale Up/Down
```bash
# Change to different tier (e.g., S1 for Standard)
az appservice plan update \
  --name vibe-coding-plan \
  --resource-group vibe-coding-rg \
  --sku S1

# Scale out (add instances)
az appservice plan update \
  --name vibe-coding-plan \
  --resource-group vibe-coding-rg \
  --number-of-workers 2
```

## Security Best Practices

### 1. Use Azure Key Vault
```bash
# Create Key Vault
az keyvault create \
  --name vibe-coding-vault \
  --resource-group vibe-coding-rg \
  --location eastus

# Add secrets to Key Vault
az keyvault secret set \
  --vault-name vibe-coding-vault \
  --name master-db-url \
  --value "$MASTER_DB_URL"

# Grant app access to Key Vault
az webapp identity assign \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend

# Get the principal ID
principalId=$(az webapp identity show \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --query principalId --output tsv)

# Grant access to Key Vault
az keyvault set-policy \
  --name vibe-coding-vault \
  --object-id $principalId \
  --secret-permissions get list
```

### 2. Configure CORS (if needed)
```bash
az webapp cors add \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --allowed-origins "https://your-frontend.com"
```

### 3. Enable HTTPS Only
```bash
az webapp update \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --https-only true
```

## Troubleshooting

### Application won't start
1. Check logs: `az webapp log tail --resource-group vibe-coding-rg --name vibe-coding-backend`
2. Verify Python version: Should be 3.11
3. Check startup command in Azure Portal → Configuration → General settings

### Database connection issues
1. Verify environment variables are set
2. Check if Azure PostgreSQL allows connections from App Service
3. Ensure SSL is configured correctly

### Slow performance
1. Scale up to higher tier (B1 → S1 → P1V2)
2. Enable Always On: `az webapp config set --resource-group vibe-coding-rg --name vibe-coding-backend --always-on true`
3. Check database performance

## Costs

Approximate monthly costs:
- **B1 (Basic)**: ~$13/month - Good for development
- **S1 (Standard)**: ~$70/month - Good for production
- **P1V2 (Premium)**: ~$150/month - For high traffic

## URLs

After deployment, your API will be available at:
- **Base URL**: `https://vibe-coding-backend.azurewebsites.net`
- **Health Check**: `https://vibe-coding-backend.azurewebsites.net/api/health`
- **Swagger UI**: `https://vibe-coding-backend.azurewebsites.net/docs`

## Support

- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [Python on Azure](https://docs.microsoft.com/en-us/azure/developer/python/)
- [Azure CLI Reference](https://docs.microsoft.com/en-us/cli/azure/)