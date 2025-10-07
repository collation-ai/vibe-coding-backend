# Vibe Coding Backend - Admin Dashboard

A beautiful, modern web interface for managing users, API keys, database assignments, and permissions for the Vibe Coding Backend.

## Features

- 👥 **User Management** - Create, activate, and deactivate users
- 🔑 **API Key Management** - Generate and revoke API keys
- 💾 **Database Assignments** - Assign PostgreSQL databases to users
- 🛡️ **Permission Management** - Grant and revoke schema-level permissions

## Quick Start

### 1. Start the Backend Server

```bash
cd /path/to/vibe-coding-backend
python3 main.py
```

The server will start on `http://localhost:8000`

### 2. Access the Admin Dashboard

Open your browser and navigate to:
```
http://localhost:8000/admin
```

### 3. Login with Your API Key

- You need an admin API key to access the dashboard
- Use an existing API key from your database
- Or create one using the Python scripts

## Usage Guide

### Creating a New User

1. Click the **"Users"** tab
2. Click **"+ Create User"**
3. Fill in the form:
   - **Email** (required): User's email address
   - **Username** (optional): Defaults to email
   - **Password** (required): Minimum 8 characters
   - **Organization** (optional): Company or team name
4. Click **"Create User"**

### Generating an API Key

1. Click the **"API Keys"** tab
2. Click **"+ Generate API Key"**
3. Fill in the form:
   - **User**: Select the user
   - **Key Name**: Descriptive name (e.g., "Production Key")
   - **Environment**: Production or Development
   - **Expires In**: Optional expiration in days
4. Click **"Generate Key"**
5. **IMPORTANT**: Copy the API key immediately - it cannot be retrieved later!

### Assigning a Database

1. Click the **"Databases"** tab
2. Click **"+ Assign Database"**
3. Fill in the form:
   - **User**: Select the user
   - **Database Name**: Name identifier (e.g., "user_db_001")
   - **Connection String**: Full PostgreSQL connection string
     ```
     postgresql://username:password@host:5432/database?sslmode=require
     ```
4. Click **"Assign Database"**
5. The connection string will be encrypted before storage

### Granting Permissions

1. Click the **"Permissions"** tab
2. Click **"+ Grant Permission"**
3. Fill in the form:
   - **User**: Select the user
   - **Database**: Select from user's assigned databases
   - **Schema Name**: PostgreSQL schema (e.g., "public")
   - **Permission Level**:
     - **Read Only**: SELECT queries only
     - **Read & Write**: All operations (SELECT, INSERT, UPDATE, DELETE, CREATE, etc.)
4. Click **"Grant Permission"**

## Security Features

- **HttpOnly Sessions**: Admin sessions are secure
- **API Key Authentication**: All operations require valid API key
- **Encrypted Storage**: Database connection strings are encrypted
- **Audit Logging**: All operations are logged
- **Password Hashing**: User passwords are bcrypt-hashed

## API Endpoints Used

The admin dashboard uses these backend endpoints:

### Users
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `POST /api/admin/users/{id}/activate` - Activate user
- `POST /api/admin/users/{id}/deactivate` - Deactivate user
- `GET /api/admin/users/{id}/databases` - Get user's databases

### API Keys
- `GET /api/admin/api-keys` - List all API keys
- `POST /api/admin/api-keys` - Generate new API key
- `POST /api/admin/api-keys/{id}/revoke` - Revoke API key

### Database Assignments
- `GET /api/admin/database-assignments` - List all assignments
- `POST /api/admin/database-assignments` - Assign database
- `DELETE /api/admin/database-assignments/{id}` - Remove assignment

### Permissions
- `GET /api/admin/permissions` - List all permissions
- `POST /api/admin/permissions` - Grant permission
- `DELETE /api/admin/permissions/{id}` - Revoke permission

## Files Structure

```
admin/
├── index.html      # Main HTML interface
├── styles.css      # Beautiful gradient styling
├── admin.js        # JavaScript logic and API calls
└── README.md       # This file
```

## Configuration

The admin dashboard automatically detects the environment:

- **Development**: `http://localhost:8000`
- **Production**: Uses current domain

You can customize the API base URL by editing `admin.js`:

```javascript
const API_BASE_URL = 'https://your-api-domain.com';
```

## Troubleshooting

### "Invalid API key" Error

- Ensure your API key is valid and active
- Check that the key hasn't expired
- Verify the user account is active

### "Failed to load users" Error

- Check that the backend server is running
- Verify database connection is working
- Check browser console for detailed errors

### Session Expired

- Login again with your API key
- Sessions are stored in localStorage
- Clear browser cache if issues persist

### CORS Errors

- Ensure CORS is configured in `main.py`
- Check `Access-Control-Allow-Origin` headers
- Verify the API base URL is correct

## Browser Compatibility

The admin dashboard works on:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers

## Development

To modify the admin dashboard:

1. Edit the HTML/CSS/JS files
2. Reload the page in your browser
3. Changes are reflected immediately (no build step needed)

### Adding New Features

1. Add HTML elements in `index.html`
2. Style them in `styles.css`
3. Add functionality in `admin.js`
4. Create corresponding backend endpoints in `api/admin.py`

## Screenshots

The dashboard features:
- 🎨 Beautiful purple gradient background
- 📊 Clean, modern table layouts
- 🎯 Intuitive tab navigation
- ✨ Smooth animations and transitions
- 📱 Fully responsive design

## Production Deployment

For production use:

1. **Secure the Admin Endpoint**:
   - Add IP whitelist if needed
   - Use HTTPS only
   - Consider adding additional authentication

2. **Environment Variables**:
   - Set production API base URL
   - Configure CORS properly
   - Use secure session storage

3. **Performance**:
   - Enable gzip compression
   - Use CDN for static assets
   - Cache API responses where appropriate

## Support

For issues or questions:
1. Check the backend server logs
2. Review browser console for errors
3. Verify database connectivity
4. Check API endpoint responses

## License

This admin dashboard is part of the Vibe Coding Backend project.
