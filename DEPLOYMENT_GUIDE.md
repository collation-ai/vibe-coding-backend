# 🚀 Vercel Deployment Guide

## Prerequisites
- Vercel account ([vercel.com](https://vercel.com))
- GitHub account with your repository
- Azure PostgreSQL database credentials

## Step 1: Prepare Environment Variables

You need these 4 environment variables:

1. **MASTER_DB_URL** - Your PostgreSQL connection string
   ```
   postgresql://username:password@server.postgres.database.azure.com:5432/database?sslmode=require
   ```

2. **AZURE_DB_HOST** - Your Azure PostgreSQL host
   ```
   your-server.postgres.database.azure.com
   ```

3. **ENCRYPTION_KEY** - Generate using:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **API_KEY_SALT** - Generate using:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## Step 2: Deploy via GitHub Integration

### A. Connect Repository to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Import Git Repository"
3. Select your GitHub repository
4. Choose the repository containing the backend code

### B. Configure Project

1. **Framework Preset**: Select "Other"
2. **Root Directory**: Leave as `.` (or select if in subdirectory)
3. **Build Command**: Leave default or set to `pip install -r requirements.txt`

### C. Add Environment Variables

Click "Environment Variables" and add:

| Key | Value | Environment |
|-----|-------|-------------|
| MASTER_DB_URL | `postgresql://...` | Production |
| AZURE_DB_HOST | `server.postgres.database.azure.com` | Production |
| ENCRYPTION_KEY | (generated key) | Production |
| API_KEY_SALT | (generated salt) | Production |

### D. Deploy

Click "Deploy" and wait for the build to complete.

## Step 3: Verify Deployment

Once deployed, test your endpoints:

```bash
# Test health endpoint
curl https://your-project.vercel.app/api/health

# Test authentication (use your API key)
curl -X POST https://your-project.vercel.app/api/auth/validate \
  -H "X-API-Key: vibe_prod_YOUR_KEY" \
  -H "Content-Type: application/json"
```

## Alternative: Deploy via Vercel CLI

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Set Environment Variables
```bash
# Add each environment variable
vercel env add MASTER_DB_URL production
# (paste your connection string when prompted)

vercel env add AZURE_DB_HOST production
# (paste your host when prompted)

vercel env add ENCRYPTION_KEY production
# (paste generated key when prompted)

vercel env add API_KEY_SALT production
# (paste generated salt when prompted)
```

### 4. Deploy
```bash
# Deploy to production
vercel --prod
```

## Troubleshooting

### Error: "Environment Variable references Secret which does not exist"

**Solution**: The `vercel.json` file uses `@secret_name` syntax. Either:
1. Add the secrets in Vercel Dashboard under Settings → Environment Variables
2. Use the simplified `vercel_simple.json` instead:
   ```bash
   mv vercel.json vercel_original.json
   mv vercel_simple.json vercel.json
   ```

### Error: "Module not found"

**Solution**: Ensure all dependencies are in `requirements.txt`:
```bash
pip freeze > requirements.txt
```

### Error: "Function timeout"

**Solution**: Check that your database allows connections from Vercel's IP ranges. For Azure:
1. Go to Azure Portal → Your PostgreSQL Server
2. Navigate to "Connection security"
3. Add firewall rule: Start IP `0.0.0.0` End IP `255.255.255.255` (for testing)
4. For production, use specific Vercel IP ranges

### Error: "Cannot connect to database"

**Solution**: Verify your connection string:
- Ensure `sslmode=require` is included
- Check username format (might need `username@servername` for Azure)
- Verify password doesn't contain special characters that need URL encoding

## Post-Deployment Steps

1. **Initialize Database**
   ```bash
   # Run locally with production database
   export MASTER_DB_URL="your_production_connection_string"
   python scripts/init_db.py
   ```

2. **Create Users**
   ```bash
   python scripts/admin.py --create-user "user@example.com" --org "Organization"
   python scripts/admin.py --generate-key "user@example.com" --key-name "Production" --env prod
   ```

3. **Test API**
   ```bash
   # Update test script with your Vercel URL
   BASE_URL="https://your-project.vercel.app"
   python test_complete.py
   ```

## Security Notes

1. **Never commit** `.env` files or secrets to Git
2. **Use different** encryption keys for development and production
3. **Restrict** database access to specific IP ranges in production
4. **Monitor** API usage through Vercel Analytics
5. **Set up** alerts for failed authentication attempts

## Useful Commands

```bash
# View deployment logs
vercel logs

# List environment variables
vercel env ls

# Remove environment variable
vercel env rm VARIABLE_NAME

# Redeploy
vercel --prod --force

# View project info
vercel inspect
```

## Support

For issues:
1. Check Vercel Function Logs in dashboard
2. Review deployment logs: `vercel logs`
3. Test locally first: `python main.py`
4. Verify database connectivity from local machine