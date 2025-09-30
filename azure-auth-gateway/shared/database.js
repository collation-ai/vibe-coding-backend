const { Client } = require('pg');

let client = null;

async function getDbClient() {
    if (!client) {
        client = new Client({
            connectionString: process.env.MASTER_DB_URL,
            ssl: {
                rejectUnauthorized: false
            }
        });
        await client.connect();
    }
    return client;
}

async function validateUserCredentials(username, password) {
    const bcrypt = require('bcryptjs');
    const client = await getDbClient();
    
    try {
        const query = `
            SELECT id, username, email, password_hash, organization, is_active
            FROM users 
            WHERE (username = $1 OR email = $1) AND is_active = true
        `;
        const result = await client.query(query, [username]);
        
        if (result.rows.length === 0) {
            return null;
        }
        
        const user = result.rows[0];
        const validPassword = await bcrypt.compare(password, user.password_hash);
        
        if (!validPassword) {
            return null;
        }
        
        // Don't return the password hash
        delete user.password_hash;
        return user;
    } catch (error) {
        console.error('Error validating user credentials:', error);
        throw error;
    }
}

async function getUserPermissions(userId) {
    const client = await getDbClient();
    
    try {
        const query = `
            SELECT 
                sp.database_name,
                sp.schema_name,
                sp.permission,
                da.connection_string_encrypted
            FROM schema_permissions sp
            LEFT JOIN database_assignments da 
                ON sp.user_id = da.user_id 
                AND sp.database_name = da.database_name
            WHERE sp.user_id = $1
        `;
        const result = await client.query(query, [userId]);
        
        const permissions = {
            databases: {},
            schemas: []
        };
        
        result.rows.forEach(row => {
            if (!permissions.databases[row.database_name]) {
                permissions.databases[row.database_name] = {
                    schemas: {}
                };
            }
            permissions.databases[row.database_name].schemas[row.schema_name] = row.permission;
            permissions.schemas.push(`${row.database_name}.${row.schema_name}`);
        });
        
        return permissions;
    } catch (error) {
        console.error('Error getting user permissions:', error);
        throw error;
    }
}

async function logApiCall(userId, endpoint, method, statusCode, errorMessage = null) {
    const client = await getDbClient();
    
    try {
        const query = `
            INSERT INTO audit_logs (
                user_id, endpoint, method, response_status, 
                error_message, created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW())
        `;
        await client.query(query, [userId, endpoint, method, statusCode, errorMessage]);
    } catch (error) {
        console.error('Error logging API call:', error);
        // Don't throw - logging errors shouldn't break the API
    }
}

module.exports = {
    getDbClient,
    validateUserCredentials,
    getUserPermissions,
    logApiCall
};