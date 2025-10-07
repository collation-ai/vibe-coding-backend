const { TableClient } = require("@azure/data-tables");
const { v4: uuidv4 } = require('uuid');

let tableClient = null;

async function getTableClient() {
    if (!tableClient) {
        tableClient = TableClient.fromConnectionString(
            process.env.AZURE_STORAGE_CONNECTION,
            "sessions"
        );
        
        // Create table if it doesn't exist
        try {
            await tableClient.createTable();
        } catch (error) {
            // Table already exists, that's fine
            if (error.statusCode !== 409) {
                console.error('Error creating sessions table:', error);
            }
        }
    }
    return tableClient;
}

async function createSession(userId, username, csrfToken, database) {
    const sessionId = uuidv4();
    const expiresAt = new Date(Date.now() + (parseInt(process.env.SESSION_TIMEOUT_MINUTES || 60) * 60000));
    
    const client = await getTableClient();
    
    const entity = {
        partitionKey: "session",
        rowKey: sessionId,
        userId: userId,
        username: username,
        csrfToken: csrfToken,
        database: database || 'cdb_written_976_poetry',  // Store selected database
        createdAt: new Date(),
        expiresAt: expiresAt,
        lastActivityAt: new Date()
    };
    
    try {
        await client.createEntity(entity);
        return {
            sessionId,
            csrfToken,
            expiresAt
        };
    } catch (error) {
        console.error('Error creating session:', error);
        throw error;
    }
}

async function getSession(sessionId) {
    if (!sessionId) return null;
    
    const client = await getTableClient();
    
    try {
        const entity = await client.getEntity("session", sessionId);
        
        // Check if session is expired
        if (new Date(entity.expiresAt) < new Date()) {
            // Delete expired session
            await deleteSession(sessionId);
            return null;
        }
        
        // Update last activity
        entity.lastActivityAt = new Date();
        await client.updateEntity(entity, "Merge");
        
        return entity;
    } catch (error) {
        if (error.statusCode === 404) {
            return null;
        }
        console.error('Error getting session:', error);
        throw error;
    }
}

async function deleteSession(sessionId) {
    const client = await getTableClient();
    
    try {
        await client.deleteEntity("session", sessionId);
    } catch (error) {
        if (error.statusCode !== 404) {
            console.error('Error deleting session:', error);
        }
    }
}

async function cleanupExpiredSessions() {
    const client = await getTableClient();
    
    try {
        const sessions = client.listEntities({
            filter: `partitionKey eq 'session'`
        });
        
        for await (const session of sessions) {
            if (new Date(session.expiresAt) < new Date()) {
                await deleteSession(session.rowKey);
            }
        }
    } catch (error) {
        console.error('Error cleaning up sessions:', error);
    }
}

module.exports = {
    createSession,
    getSession,
    deleteSession,
    cleanupExpiredSessions
};