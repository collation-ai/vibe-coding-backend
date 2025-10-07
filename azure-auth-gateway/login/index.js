const { validateUserCredentials, logApiCall } = require('../shared/database');
const { createSession } = require('../shared/sessions');
const { getCorsHeaders } = require('../shared/cors');
const { v4: uuidv4 } = require('uuid');

module.exports = async function (context, req) {
    context.log('Login endpoint called');
    
    // Set CORS headers
    context.res = {
        headers: getCorsHeaders(req)
    };
    
    // Handle preflight
    if (req.method === 'OPTIONS') {
        context.res.status = 204;
        return;
    }
    
    try {
        const { username, password, database } = req.body;
        
        if (!username || !password || !database) {
            context.res.status = 400;
            context.res.body = {
                success: false,
                error: 'Username, password, and database are required'
            };
            await logApiCall(null, '/api/login', 'POST', 400, 'Missing credentials');
            return;
        }
        
        // Validate credentials
        const user = await validateUserCredentials(username, password);
        
        if (!user) {
            context.res.status = 401;
            context.res.body = {
                success: false,
                error: 'Invalid credentials'
            };
            await logApiCall(null, '/api/login', 'POST', 401, 'Invalid credentials');
            return;
        }
        
        // Create session with database info
        const csrfToken = uuidv4();
        const session = await createSession(user.id, user.username, csrfToken, database);
        
        // Set httpOnly cookie
        context.res.cookies = [{
            name: "vibe_session",
            value: session.sessionId,
            httpOnly: true,
            secure: true,
            sameSite: "None", // Required for cross-origin requests from Lovable
            maxAge: parseInt(process.env.SESSION_TIMEOUT_MINUTES || 60) * 60,
            path: "/"
        }];
        
        // Return success with CSRF token (session ID is only in httpOnly cookie)
        context.res.status = 200;
        context.res.body = {
            success: true,
            data: {
                csrfToken: session.csrfToken,
                username: user.username,
                email: user.email,
                organization: user.organization,
                database: database,
                expiresIn: parseInt(process.env.SESSION_TIMEOUT_MINUTES || 60) * 60
            }
        };
        
        await logApiCall(user.id, '/api/login', 'POST', 200);
        
    } catch (error) {
        context.log.error('Login error:', error);
        context.res.status = 500;
        context.res.body = {
            success: false,
            error: 'Internal server error'
        };
        await logApiCall(null, '/api/login', 'POST', 500, error.message);
    }
};