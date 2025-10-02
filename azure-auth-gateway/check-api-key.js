const { Client } = require('pg');

async function checkApiKey() {
    const connectionString = "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require";
    
    const client = new Client({
        connectionString: connectionString,
        ssl: {
            rejectUnauthorized: false
        }
    });
    
    try {
        await client.connect();
        console.log('Connected to database\n');
        
        // Check if the API key exists
        const apiKey = 'vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ';
        console.log('Checking API key:', apiKey);
        
        // First, let's see what's in the api_keys table
        const allKeys = await client.query(`
            SELECT 
                ak.key_prefix,
                ak.name,
                ak.is_active,
                u.username,
                u.email
            FROM api_keys ak
            LEFT JOIN users u ON ak.user_id = u.id
            ORDER BY ak.created_at DESC
            LIMIT 10
        `);
        
        console.log('\nExisting API keys in database:');
        if (allKeys.rows.length === 0) {
            console.log('  No API keys found');
        } else {
            allKeys.rows.forEach(key => {
                console.log(`  - ${key.key_prefix}... (${key.name}) - User: ${key.username || key.email} - Active: ${key.is_active}`);
            });
        }
        
        // Check if we need to create this API key
        const crypto = require('crypto');
        const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');
        
        const existingKey = await client.query(
            'SELECT * FROM api_keys WHERE key_hash = $1',
            [keyHash]
        );
        
        if (existingKey.rows.length > 0) {
            console.log('\n✅ API key already exists in database');
        } else {
            console.log('\n❌ API key NOT found in database');
            console.log('\nTo fix this, we need to:');
            console.log('1. Create the API key in the database');
            console.log('2. Link it to a user');
            console.log('3. Grant permissions\n');
            
            // Get tanmais user
            const userResult = await client.query(
                "SELECT id, username, email FROM users WHERE username = 'tanmais' OR email = 'tanmais@vibe-coding.com'"
            );
            
            if (userResult.rows.length > 0) {
                const user = userResult.rows[0];
                console.log(`Found user: ${user.username} (${user.email})`);
                console.log('\nWould you like to create the API key? Run:');
                console.log('node setup-api-key.js');
            }
        }
        
        await client.end();
        
    } catch (error) {
        console.error('Error:', error.message);
        await client.end();
    }
}

checkApiKey();