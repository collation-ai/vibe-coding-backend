# Lovable.dev Integration Guide

## Overview
This guide explains how to integrate your Lovable.dev application with the secure Azure Functions authentication gateway.

## Architecture
```
Lovable App → Azure Auth Gateway → Vibe Backend → PostgreSQL
```

## Setup Steps

### 1. Environment Variables
Add these to your Lovable app's environment variables:
```
VIBE_AUTH_GATEWAY_URL=https://vibe-auth-gateway.azurewebsites.net
```

### 2. Create Authentication Service
Create a new file `services/auth.js` in your Lovable app:

```javascript
class AuthService {
  constructor() {
    this.baseUrl = process.env.VIBE_AUTH_GATEWAY_URL || 'https://vibe-auth-gateway.azurewebsites.net';
    this.csrfToken = null;
    this.user = null;
  }

  async login(username, password) {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include', // IMPORTANT: This enables cookies
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Login failed');
      }

      const data = await response.json();
      
      // Store CSRF token and user info
      this.csrfToken = data.data.csrfToken;
      this.user = {
        username: data.data.username,
        email: data.data.email,
        organization: data.data.organization
      };
      
      // Store in localStorage for persistence
      localStorage.setItem('csrfToken', this.csrfToken);
      localStorage.setItem('user', JSON.stringify(this.user));
      
      return data.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  async logout() {
    try {
      await fetch(`${this.baseUrl}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      
      // Clear stored data
      this.csrfToken = null;
      this.user = null;
      localStorage.removeItem('csrfToken');
      localStorage.removeItem('user');
      
      // Redirect to login
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  isAuthenticated() {
    return this.csrfToken !== null;
  }

  loadFromStorage() {
    this.csrfToken = localStorage.getItem('csrfToken');
    const userStr = localStorage.getItem('user');
    if (userStr) {
      this.user = JSON.parse(userStr);
    }
  }
}

export const authService = new AuthService();
```

### 3. Create Database Service
Create `services/database.js`:

```javascript
import { authService } from './auth';

class DatabaseService {
  constructor() {
    this.baseUrl = process.env.VIBE_AUTH_GATEWAY_URL || 'https://vibe-auth-gateway.azurewebsites.net';
  }

  async request(endpoint, options = {}) {
    // Ensure we have a CSRF token
    if (!authService.csrfToken) {
      authService.loadFromStorage();
      if (!authService.csrfToken) {
        throw new Error('Not authenticated');
      }
    }

    const url = `${this.baseUrl}/api/proxy/${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': authService.csrfToken,
        ...(options.headers || {})
      },
      credentials: 'include' // Always include cookies
    });

    if (response.status === 401) {
      // Session expired
      authService.logout();
      return;
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  // Table operations
  async listTables(database, schema = 'public') {
    return this.request('tables', {
      method: 'GET',
      headers: {
        'X-Database-Name': database
      }
    });
  }

  async createTable(database, schema, tableName, columns) {
    return this.request('tables', {
      method: 'POST',
      body: JSON.stringify({
        database,
        schema,
        table: tableName,
        columns
      })
    });
  }

  // Data operations
  async queryData(database, schema, table, filters = {}) {
    const params = new URLSearchParams(filters).toString();
    return this.request(`data/${schema}/${table}?${params}`, {
      method: 'GET',
      headers: {
        'X-Database-Name': database
      }
    });
  }

  async insertData(database, schema, table, data) {
    return this.request(`data/${schema}/${table}`, {
      method: 'POST',
      headers: {
        'X-Database-Name': database
      },
      body: JSON.stringify(data)
    });
  }

  async updateData(database, schema, table, id, data) {
    return this.request(`data/${schema}/${table}`, {
      method: 'PUT',
      headers: {
        'X-Database-Name': database
      },
      body: JSON.stringify({
        where: { id },
        data
      })
    });
  }

  async deleteData(database, schema, table, id) {
    return this.request(`data/${schema}/${table}`, {
      method: 'DELETE',
      headers: {
        'X-Database-Name': database
      },
      body: JSON.stringify({
        where: { id }
      })
    });
  }

  // Raw SQL
  async executeQuery(database, query, params = []) {
    return this.request('query', {
      method: 'POST',
      body: JSON.stringify({
        database,
        query,
        params
      })
    });
  }
}

export const databaseService = new DatabaseService();
```

### 4. Create Login Component
Create `components/Login.jsx`:

```jsx
import React, { useState } from 'react';
import { authService } from '../services/auth';

export function Login({ onSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(username, password);
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit}>
        <h2>Login to Vibe Coding</h2>
        
        {error && (
          <div className="error-message">{error}</div>
        )}
        
        <div className="form-group">
          <label>Username or Email</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
```

### 5. App Component with Auth
Update your main `App.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import { Login } from './components/Login';
import { authService } from './services/auth';
import { databaseService } from './services/database';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    authService.loadFromStorage();
    setIsAuthenticated(authService.isAuthenticated());
    setLoading(false);
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    await authService.logout();
    setIsAuthenticated(false);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app">
      <header>
        <h1>Vibe Coding Dashboard</h1>
        <div className="user-info">
          Welcome, {authService.user?.username}
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>
      
      <main>
        {/* Your app content here */}
        <DatabaseOperations />
      </main>
    </div>
  );
}

function DatabaseOperations() {
  const [tables, setTables] = useState([]);
  const [data, setData] = useState([]);

  const loadTables = async () => {
    try {
      const result = await databaseService.listTables('my_database');
      setTables(result.data);
    } catch (error) {
      console.error('Failed to load tables:', error);
    }
  };

  const loadData = async (table) => {
    try {
      const result = await databaseService.queryData('my_database', 'public', table);
      setData(result.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  useEffect(() => {
    loadTables();
  }, []);

  return (
    <div>
      <h2>Database Operations</h2>
      {/* Your database UI here */}
    </div>
  );
}

export default App;
```

## Security Notes

1. **CSRF Token**: Always include the CSRF token in headers for API calls
2. **Credentials**: Always use `credentials: 'include'` to send cookies
3. **Session Expiry**: Handle 401 responses by redirecting to login
4. **Storage**: Only store CSRF token in localStorage (safe), never passwords
5. **HTTPS**: Always use HTTPS in production

## Testing

Test the integration:

1. Open browser DevTools Network tab
2. Try logging in - you should see:
   - Cookie set (vibe_session - httpOnly)
   - CSRF token in response
3. Make an API call - you should see:
   - Cookie automatically sent
   - CSRF token in headers
4. Check that session expires after timeout

## Troubleshooting

### CORS Issues
If you see CORS errors:
- Ensure Azure Function CORS is configured for your Lovable domain
- Check that `credentials: 'include'` is set on all requests

### Session Not Persisting
- Verify cookies are enabled in browser
- Check that you're using HTTPS (required for secure cookies)
- Ensure `sameSite: "None"` is set in cookie configuration

### 401 Unauthorized
- Session has expired - redirect to login
- CSRF token missing or invalid
- Cookie not being sent - check `credentials: 'include'`

## Support

For issues, check:
1. Azure Function logs in Application Insights
2. Browser console for JavaScript errors
3. Network tab for failed requests
4. Audit logs in the master database