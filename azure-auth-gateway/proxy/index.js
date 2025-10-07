const fetch = require('node-fetch');
const { getSession } = require('../shared/sessions');
const { getUserPermissions, logApiCall } = require('../shared/database');
const { getCorsHeaders } = require('../shared/cors');

module.exports = async function (context, req) {
    context.log('Proxy endpoint called:', req.method, req.params.path);
    
    // Set CORS headers
    context.res = {
        headers: getCorsHeaders(req)
    };
    
    // Handle preflight
    if (req.method === 'OPTIONS') {
        context.res.status = 204;
        return;
    }
    
    let userId = null;
    
    try {
        // Get session from cookie OR header (for cross-site scenarios)
        const cookies = parseCookies(req.headers.cookie || '');
        const sessionId = cookies.vibe_session || req.headers['x-session-id'];
        const csrfToken = req.headers['x-csrf-token'];

        context.log('Session ID source:', cookies.vibe_session ? 'cookie' : req.headers['x-session-id'] ? 'header' :
        'none');
        context.log('Session ID value:', sessionId);        
        if (!sessionId) {
            context.res.status = 401;
            context.res.body = {
                success: false,
                error: 'No session found. Please login.'
            };
            await logApiCall(null, req.params.path, req.method, 401, 'No session');
            return;
        }
        
        // Validate session
        const session = await getSession(sessionId);
        
        if (!session) {
            context.res.status = 401;
            context.res.body = {
                success: false,
                error: 'Session expired or invalid. Please login again.'
            };
            await logApiCall(null, req.params.path, req.method, 401, 'Invalid session');
            return;
        }
        
        userId = session.userId;
        
        // Validate CSRF token
        if (session.csrfToken !== csrfToken) {
            context.res.status = 403;
            context.res.body = {
                success: false,
                error: 'Invalid CSRF token'
            };
            await logApiCall(userId, req.params.path, req.method, 403, 'Invalid CSRF token');
            return;
        }
        
        // Get user permissions
        const permissions = await getUserPermissions(userId);
        
        // Build the backend URL
        // The path already includes /api/ from the backend, so we just append the path
        const backendUrl = `${process.env.VIBE_BACKEND_URL}/${req.params.path || ''}`;
        const queryString = req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '';
        const fullUrl = backendUrl + queryString;
        
        context.log('Forwarding to:', fullUrl);
        
        // Prepare headers for backend
        const headers = {
            'X-API-Key': process.env.VIBE_REAL_API_KEY,
            'X-User-Id': userId,
            'X-Username': session.username,
            'Content-Type': req.headers['content-type'] || 'application/json'
        };
        
        // Add database name from session or request
        // Priority: request body > header > session
        let databaseName = session.database || 'cdb_written_976_poetry';
        if (req.body && req.body.database) {
            databaseName = req.body.database;
        } else if (req.headers['x-database-name']) {
            databaseName = req.headers['x-database-name'];
        }
        headers['X-Database-Name'] = databaseName;
        context.log('Using database:', databaseName);
        
        // Forward the request
        const options = {
            method: req.method,
            headers: headers
        };
        
        // Add body for non-GET requests
        if (req.method !== 'GET' && req.method !== 'HEAD' && req.body) {
            options.body = JSON.stringify(req.body);
        }
        
        const response = await fetch(fullUrl, options);
        const responseText = await response.text();
        
        let responseData;
        try {
            responseData = JSON.parse(responseText);
        } catch {
            responseData = responseText;
        }
        
        // Return the response
        context.res.status = response.status;
        context.res.body = responseData;
        
        // Log the API call
        await logApiCall(
            userId, 
            req.params.path, 
            req.method, 
            response.status,
            response.ok ? null : responseData.error || 'Unknown error'
        );
        
    } catch (error) {
        context.log.error('Proxy error:', error);
        context.res.status = 500;
        context.res.body = {
            success: false,
            error: 'Internal server error'
        };
        await logApiCall(userId, req.params.path, req.method, 500, error.message);
    }
};

function parseCookies(cookieStr) {
    const cookies = {};
    if (!cookieStr) return cookies;
    
    cookieStr.split(';').forEach(cookie => {
        const parts = cookie.trim().split('=');
        if (parts.length === 2) {
            cookies[parts[0]] = parts[1];
        }
    });
    
    return cookies;
}