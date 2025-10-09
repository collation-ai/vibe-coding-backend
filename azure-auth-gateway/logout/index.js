const { deleteSession } = require('../shared/sessions');
const { logApiCall } = require('../shared/database');
const { getCorsHeaders } = require('../shared/cors');

module.exports = async function (context, req) {
    context.log('Logout endpoint called');

    // Get CORS headers
    const corsHeaders = getCorsHeaders(req);

    // Handle preflight
    if (req.method === 'OPTIONS') {
        context.res = {
            status: 204,
            headers: corsHeaders,
            body: null
        };
        context.done();
        return;
    }

    // Set CORS headers for regular requests
    context.res = {
        headers: corsHeaders
    };
    
    try {
        // Get session from cookie
        const cookies = parseCookies(req.headers.cookie || '');
        const sessionId = cookies.vibe_session;
        
        if (sessionId) {
            // Delete the session
            await deleteSession(sessionId);
        }
        
        // Clear the cookie
        context.res.cookies = [{
            name: "vibe_session",
            value: "",
            httpOnly: true,
            secure: true,
            sameSite: "None",
            maxAge: 0,
            path: "/"
        }];
        
        context.res.status = 200;
        context.res.body = {
            success: true,
            message: 'Logged out successfully'
        };
        
        await logApiCall(null, '/api/logout', 'POST', 200);
        
    } catch (error) {
        context.log.error('Logout error:', error);
        context.res.status = 500;
        context.res.body = {
            success: false,
            error: 'Internal server error'
        };
        await logApiCall(null, '/api/logout', 'POST', 500, error.message);
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