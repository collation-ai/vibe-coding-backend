// CORS helper for Azure Functions
function getCorsHeaders(req) {
    const origin = req.headers.origin || req.headers.Origin || '';
    const allowedOrigins = (process.env.ALLOWED_ORIGINS || '').split(',').map(o => o.trim());
    
    // Special handling for Lovable.dev and Lovable.app - allow any subdomain
    if (origin && (origin.includes('lovable.dev') || origin.includes('lovable.app'))) {
        console.log('Lovable origin detected:', origin);
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
            'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Session-Id, X-Database-Name, X-API-Key, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Expose-Headers': 'X-Session-Id, X-CSRF-Token'
        };
    }
    
    // Check against allowed origins list
    const isAllowed = allowedOrigins.some(allowed => {
        if (allowed.includes('*')) {
            // Convert wildcard to regex pattern
            const pattern = allowed.replace(/\*/g, '.*').replace(/\./g, '\\.');
            const regex = new RegExp(`^${pattern}$`);
            return regex.test(origin);
        }
        return allowed === origin;
    });
    
    // If origin is allowed, use it; otherwise use the first allowed origin (for dev)
    const corsOrigin = isAllowed ? origin : allowedOrigins[0] || '*';
    
    console.log('Request origin:', origin, 'CORS origin:', corsOrigin);
    
    return {
        'Access-Control-Allow-Origin': corsOrigin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
        'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token, X-Session-Id, X-Database-Name, X-API-Key, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Expose-Headers': 'X-Session-Id, X-CSRF-Token'
    };
}

module.exports = { getCorsHeaders };