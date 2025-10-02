# Vibe Coding Backend - Testing Guide

This guide explains how to test the authentication gateway and backend API locally and in production.

## Table of Contents
- [Overview](#overview)
- [Local Testing Scripts](#local-testing-scripts)
- [Testing the Production Gateway](#testing-the-production-gateway)
- [Common Testing Scenarios](#common-testing-scenarios)
- [Troubleshooting](#troubleshooting)

## Overview

The Vibe Coding Backend consists of two main components:
1. **Backend API** (`vibe-coding-backend.azurewebsites.net`) - The main API server
2. **Authentication Gateway** (`vibe-auth-gateway.azurewebsites.net`) - Handles user sessions and proxies requests

## Local Testing Scripts

We have three scripts for local testing that help debug issues without deploying to Azure:

### 1. test-backend-directly.py

Tests the backend API directly, bypassing the gateway entirely.

**Usage:**
```bash
python3 test-backend-directly.py
```

**What it does:**
- Uses the API key directly (no session/CSRF needed)
- Tests the `/api/auth/permissions` endpoint
- Tests with and without `X-User-Id` header
- Shows raw backend responses

**When to use:**
- To verify if the backend is working correctly
- To test permission logic
- To debug backend-specific issues

### 2. test-gateway-locally.py

Simulates what the authentication gateway does when proxying requests.

**Usage:**
```bash
python3 test-gateway-locally.py
```

**What it does:**
- Simulates the gateway's proxy behavior
- Automatically uses freshwaterapiuser's ID as an example
- Tests both `/api/auth/permissions` and `/api/query` endpoints
- Sends requests as if the gateway was making them

**When to use:**
- To test how the gateway passes user information
- To debug X-User-Id header handling
- To verify gateway-to-backend communication

### 3. test_local_fastapi.py

Runs a local FastAPI server for detailed debugging with console output.

**Usage:**
```bash
# Start the server (runs on port 8888)
python3 test_local_fastapi.py &

# Test without X-User-Id (returns tanmais's permissions)
curl http://localhost:8888/test/permissions \
  -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"

# Test with X-User-Id (returns freshwaterapiuser's permissions)
curl http://localhost:8888/test/permissions \
  -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \
  -H "X-User-Id: d4a34dc6-6699-4183-b068-6c7832291e4b"

# Kill the server when done
pkill -f test_local_fastapi
```

**What it does:**
- Runs a local version of the permissions endpoint
- Provides detailed console logging
- Shows exactly what's happening at each step

**When to use:**
- For step-by-step debugging
- To test code changes before deployment
- To understand the flow of data

## Testing the Production Gateway

The production gateway requires session-based authentication with CSRF protection.

### Step 1: Login to Get Session & CSRF Token

```bash
# Login as a user (replace with actual credentials)
curl -i -X POST "https://vibe-auth-gateway.azurewebsites.net/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"freshwaterapiuser","password":"YourPassword123#"}'
```

**Look for:**
1. **Session cookie** in response headers:
   ```
   set-cookie: vibe_session=4648fb03-527e-4422-9e35-2d0c937d6865; ...
   ```

2. **CSRF token** in JSON response body:
   ```json
   {
     "data": {
       "csrfToken": "34d053d8-95bc-48f4-91b7-c2f096f1f9ed",
       ...
     }
   }
   ```

### Step 2: Make Authenticated Requests

Use both the session cookie and CSRF token in subsequent requests:

```bash
# Get permissions
curl -X GET "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/auth/permissions" \
  -H "Cookie: vibe_session=[SESSION-ID-FROM-STEP-1]" \
  -H "X-CSRF-Token: [CSRF-TOKEN-FROM-STEP-1]"

# Execute a query
curl -X POST "https://vibe-auth-gateway.azurewebsites.net/api/proxy/api/query" \
  -H "Cookie: vibe_session=[SESSION-ID-FROM-STEP-1]" \
  -H "X-CSRF-Token: [CSRF-TOKEN-FROM-STEP-1]" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "master_db",
    "query": "SELECT COUNT(*) FROM users",
    "params": []
  }'
```

### Using Swagger UI

1. Navigate to: https://vibe-auth-gateway.azurewebsites.net/api/docs
2. Use the login endpoint to authenticate
3. **Note:** Swagger UI doesn't show the `Set-Cookie` header
4. To get the session cookie:
   - Open browser DevTools (F12)
   - Go to Network tab
   - Execute the login request
   - Check the response headers for `set-cookie`

## Common Testing Scenarios

### Test User Permissions

**Scenario:** Verify that freshwaterapiuser sees their own permissions, not tanmais's

```bash
# Using local script
python3 test-gateway-locally.py

# Or test production
# 1. Login as freshwaterapiuser
# 2. Call /api/proxy/api/auth/permissions
# Should return: cdb_written_976_poetry database, NOT master_db alone
```

### Test Database Query Access

**Scenario:** Verify user can only query databases they have access to

```bash
# Test with local script
python3 test-gateway-locally.py

# The script will test a query on master_db
# freshwaterapiuser should have access based on their permissions
```

### Test Direct Backend Access (Bypass Gateway)

**Scenario:** Verify backend API key authentication works

```bash
python3 test-backend-directly.py
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Internal Server Error" from Gateway

**Possible causes:**
- Backend deployment failed
- Database connection issues
- Code errors in backend

**How to debug:**
```bash
# Test backend directly
python3 test-backend-directly.py

# If backend is down, check deployment status
# If backend works, issue is in gateway
```

#### 2. "Invalid CSRF token"

**Cause:** CSRF token doesn't match session

**Solution:**
- Make sure you're using the CSRF token from the same login session
- Tokens are unique per session

#### 3. "Session expired or invalid"

**Cause:** Session has expired (default 60 minutes)

**Solution:**
- Login again to get a new session and CSRF token

#### 4. Permissions showing wrong user

**Cause:** X-User-Id header not being passed correctly

**How to verify:**
```bash
# Test with local script
python3 test-gateway-locally.py

# Should show different permissions for different user IDs
```

#### 5. "Object of type datetime is not JSON serializable"

**Cause:** datetime objects not converted to strings

**Solution:**
- Ensure all `datetime.utcnow()` are converted to `datetime.utcnow().isoformat()`
- Already fixed in latest version

## Quick Testing Workflow

For rapid development and debugging:

1. **Check backend health:**
   ```bash
   curl https://vibe-coding-backend.azurewebsites.net/api/health \
     -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
   ```

2. **Test your changes locally:**
   ```bash
   # Start local server
   python3 test_local_fastapi.py &
   
   # Test endpoint
   curl http://localhost:8888/test/permissions \
     -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
   
   # Stop server
   pkill -f test_local_fastapi
   ```

3. **Verify gateway behavior:**
   ```bash
   python3 test-gateway-locally.py
   ```

4. **Test in production** (after deployment):
   - Login to get session/CSRF
   - Test through gateway proxy

## Environment Variables

For local testing, these scripts use hardcoded values. In production:

- **Backend**: Uses Azure App Service configuration
- **Gateway**: Uses Azure Functions configuration

Key variables:
- `MASTER_DB_URL`: PostgreSQL connection string
- `ENCRYPTION_KEY`: For encrypting database connection strings
- `API_KEY_SALT`: For hashing API keys
- `VIBE_BACKEND_URL`: Backend API URL
- `VIBE_REAL_API_KEY`: Gateway's API key for backend

## Security Notes

⚠️ **Important:**
- Never commit credentials to git
- API keys in test scripts are for development only
- Always use environment variables in production
- Session cookies are httpOnly and secure
- CSRF tokens prevent cross-site request forgery

## User Credentials for Testing

Default test users in the system:
- **tanmais**: Admin user with master_db access
- **freshwaterapiuser**: Test user with limited permissions
- **dev_user**: Development test user
- **prod_user**: Production test user

To create new test users, use:
```bash
python3 azure-auth-gateway/create-new-user.py
```

## API Endpoints Reference

### Authentication Gateway
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/proxy/api/health` - Health check
- `GET /api/proxy/api/auth/permissions` - Get user permissions
- `POST /api/proxy/api/query` - Execute SQL query

### Backend API (Direct Access)
- `GET /api/health` - Health check
- `GET /api/auth/permissions` - Get permissions (requires API key)
- `POST /api/auth/validate` - Validate API key
- `POST /api/query` - Execute SQL query
- `GET /api/tables` - List tables
- `POST /api/tables` - Create table

## Support

For issues or questions:
1. Check this guide first
2. Review error messages in console output
3. Use local testing scripts to isolate the problem
4. Check Azure logs if needed

---

Last Updated: October 2024
Version: 1.0.0