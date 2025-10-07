const fetch = require('node-fetch');
const { getSession } = require('../shared/sessions');
const { getUserPermissions, logApiCall } = require('../shared/database');

// Configure allowed origins - can be environment variable in production
const ALLOWED_ORIGINS = [
    'http://localhost:8080',
    'http://localhost:8081',
    'https://freshwater.azurestaticapps.net',
    // Add any preview URLs as needed
    'https://freshwater-preview-*.azurestaticapps.net'
];

function getCorsOrigin(requestOrigin) {
    // Check if the request origin is in our allowed list
    if (!requestOrigin) return ALLOWED_ORIGINS[0];
    
    // Check exact matches
    if (ALLOWED_ORIGINS.includes(requestOrigin)) {
        return requestOrigin;
    }
    
    // Check wildcard patterns (for preview environments)
    for (const pattern of ALLOWED_ORIGINS) {
        if (pattern.includes('*')) {
            const regex = new RegExp(pattern.replace('*', '.*'));
            if (regex.test(requestOrigin)) {
                return requestOrigin;
            }
        }
    }
    
    // Default to first allowed origin if no match
    return ALLOWED_ORIGINS[0];
}

module.exports = async function (context, req) {
    context.log('Proxy endpoint called:', req.method, req.params.path);
    
    const requestOrigin = req.headers.origin || req.headers.referer;
    const corsOrigin = getCorsOrigin(requestOrigin);
    
    // Set CORS headers with specific origin
    context.res = {
        headers: {
            'Access-Control-Allow-Origin': corsOrigin,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Database-Name',
            'Access-Control-Allow-Credentials': 'true'
        }
    };
    
    // Handle preflight
    if (req.method === 'OPTIONS') {
        context.res.status = 204;
        return;
    }
    
    let userId = null;
    
    try {
        // Get session from cookie
        const cookies = parseCookies(req.headers.cookie || '');
        const sessionId = cookies.vibe_session;
        const csrfToken = req.headers['x-csrf-token'];
        
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
            await logApiCall(userId, req.params.path, req.method, 403, 'Invalid CSRF');
            return;
        }
        
        // Check user permissions
        const permissions = await getUserPermissions(userId);
        const requestedPath = req.params.path || '';
        
        // Check if user has access to the requested endpoint
        const hasAccess = checkEndpointAccess(requestedPath, permissions);
        
        if (!hasAccess) {
            context.res.status = 403;
            context.res.body = {
                success: false,
                error: 'Access denied to this endpoint'
            };
            await logApiCall(userId, req.params.path, req.method, 403, 'Access denied');
            return;
        }
        
        // Forward to backend
        const backendUrl = process.env.BACKEND_URL || 'https://vibe-coding-backend.azurewebsites.net';
        const targetUrl = `${backendUrl}/${requestedPath}`;
        
        context.log('Forwarding to:', targetUrl);
        
        // Forward the request
        const backendResponse = await fetch(targetUrl, {
            method: req.method,
            headers: {
                'Content-Type': req.headers['content-type'] || 'application/json',
                'X-User-Id': userId,
                'X-Database-Name': req.headers['x-database-name'] || '',
                'X-API-Key': process.env.BACKEND_API_KEY || ''
            },
            body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined
        });
        
        const responseData = await backendResponse.json();
        
        // Log successful API call
        await logApiCall(userId, req.params.path, req.method, backendResponse.status, 'Success');
        
        // Return response
        context.res.status = backendResponse.status;
        context.res.body = responseData;
        
    } catch (error) {
        context.log.error('Proxy error:', error);
        await logApiCall(userId, req.params.path, req.method, 500, error.message);
        
        context.res.status = 500;
        context.res.body = {
            success: false,
            error: 'Internal server error'
        };
    }
};

function parseCookies(cookieString) {
    const cookies = {};
    cookieString.split(';').forEach(cookie => {
        const [key, value] = cookie.trim().split('=');
        if (key && value) {
            cookies[key] = value;
        }
    });
    return cookies;
}

function checkEndpointAccess(path, permissions) {
    // Implement your access control logic here
    // For now, allow all authenticated users to access all endpoints
    return true;
}