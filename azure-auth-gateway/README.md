# Vibe Auth Gateway - Azure Functions

## Overview
Secure authentication gateway for Vibe Coding Backend using Azure Functions. This gateway handles user authentication and forwards authenticated requests to the backend API, eliminating the exposure of API keys in browser applications.

## Features
- 🔐 Secure session-based authentication
- 🍪 HttpOnly cookies (prevents XSS attacks)
- 🛡️ CSRF protection
- 📝 Full audit logging
- ⏱️ Configurable session timeout
- 🔑 No API keys in browser

## Architecture
```
Browser (Lovable App)
    ↓ [username/password]
Auth Gateway (Azure Functions)
    ↓ [validates & creates session]
    ↓ [forwards with real API key]
Backend API (Azure App Service)
    ↓
PostgreSQL (Azure Database)
```

## Prerequisites
- Azure subscription
- Azure CLI installed
- Node.js 18+ installed
- Azure Functions Core Tools v4

## Installation

### 1. Install Dependencies
```bash
cd azure-auth-gateway
npm install
```

### 2. Setup Database
Run the SQL script on your master PostgreSQL database:
```bash
psql -h your-server.postgres.database.azure.com -U admin -d master_db -f database-setup.sql
```

### 3. Create Initial User
```bash
node setup-users.js
```

### 4. Deploy to Azure
```bash
./deploy.sh
```

## Configuration

### Environment Variables
Set these in Azure Function App settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `MASTER_DB_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db?sslmode=require` |
| `VIBE_BACKEND_URL` | Your backend API URL | `https://vibe-coding-backend.azurewebsites.net` |
| `VIBE_REAL_API_KEY` | The actual API key for backend | `vibe_prod_xxxxx` |
| `AZURE_STORAGE_CONNECTION` | Azure Storage connection string | `DefaultEndpointsProtocol=https;...` |
| `JWT_SECRET` | Secret for JWT signing | `random-string-here` |
| `SESSION_TIMEOUT_MINUTES` | Session timeout in minutes | `60` |

## API Endpoints

### Authentication

#### POST `/api/auth/login`
Login with username/password.

**Request:**
```json
{
  "username": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "csrfToken": "uuid-token",
    "username": "user",
    "email": "user@example.com",
    "expiresIn": 3600
  }
}
```
Sets httpOnly cookie: `vibe_session`

#### POST `/api/auth/logout`
Logout and clear session.

### Proxy

#### `/api/proxy/*`
Forwards all requests to the backend API with authentication.

**Headers Required:**
- `X-CSRF-Token`: The CSRF token from login
- Cookie: `vibe_session` (sent automatically)

## Local Development

### 1. Configure Local Settings
Edit `local.settings.json` with your values.

### 2. Run Functions Locally
```bash
func start
```

### 3. Test Endpoints
```bash
# Login
curl -X POST http://localhost:7071/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' \
  -c cookies.txt

# Use proxy (with cookies)
curl http://localhost:7071/api/proxy/health \
  -H "X-CSRF-Token: your-csrf-token" \
  -b cookies.txt
```

## Security Features

### Session Management
- Sessions stored in Azure Table Storage
- Automatic expiry after timeout
- Activity tracking
- Secure session ID generation

### CSRF Protection
- Token required for all API calls
- Token tied to session
- Prevents cross-site request forgery

### Cookie Security
- `httpOnly`: Prevents JavaScript access
- `secure`: HTTPS only
- `sameSite`: Controls cross-origin sending

## Monitoring

### Application Insights
Monitor function performance and errors:
```bash
az monitor app-insights query \
  --app your-app-insights \
  --analytics-query "requests | where name contains 'auth'"
```

### Audit Logs
Query audit logs in PostgreSQL:
```sql
SELECT * FROM audit_logs 
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

## Troubleshooting

### Common Issues

#### "No session found"
- Cookie not being sent
- Session expired
- Check `credentials: 'include'` in fetch

#### "Invalid CSRF token"
- Token missing from headers
- Token doesn't match session
- Session recreated (login again)

#### CORS Errors
```bash
# Fix CORS
az functionapp cors add \
  --resource-group vibe-coding \
  --name vibe-auth-gateway \
  --allowed-origins "https://your-app.lovable.app"
```

### Debug Logging
Enable detailed logging:
```bash
az functionapp config appsettings set \
  --name vibe-auth-gateway \
  --resource-group vibe-coding \
  --settings "FUNCTIONS_LOGLEVEL=Debug"
```

## Performance

### Optimization Tips
1. Use Application Insights for monitoring
2. Enable Always On for production
3. Use Premium plan for better performance
4. Configure connection pooling for database

### Scaling
```bash
# Scale to Premium plan
az functionapp plan update \
  --name vibe-auth-gateway-plan \
  --resource-group vibe-coding \
  --sku EP1
```

## Maintenance

### Clean Up Expired Sessions
Sessions are auto-cleaned on access. For manual cleanup:
```javascript
// Add to a timer function
const { cleanupExpiredSessions } = require('./shared/sessions');
await cleanupExpiredSessions();
```

### Backup Configuration
```bash
# Export settings
az functionapp config appsettings list \
  --name vibe-auth-gateway \
  --resource-group vibe-coding \
  > settings-backup.json
```

## Support

For issues:
1. Check Azure Function logs
2. Review audit_logs table
3. Enable debug logging
4. Check browser console/network tab

## License
Private - Vibe Coding Backend