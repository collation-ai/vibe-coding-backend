const { Client } = require('pg');
const crypto = require('crypto');

async function fixApiKeyWithSalt() {
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
        
        // The API key and salt from Azure
        const apiKey = 'vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ';
        const salt = '7GcyvOMC7BH8k4IZ76GYnub7IOzcYU4b9P+VimRLi7E=';
        
        // Create hash with salt (matching backend logic)
        const saltedKey = apiKey + salt;
        const keyHash = crypto.createHash('sha256').update(saltedKey).digest('hex');
        
        console.log('API Key:', apiKey);
        console.log('Salt:', salt);
        console.log('Hash with salt:', keyHash);
        
        // Get tanmais user
        const userResult = await client.query(
            "SELECT id, username, email FROM users WHERE username = 'tanmais'"
        );
        
        if (userResult.rows.length === 0) {
            console.error('❌ User tanmais not found!');
            await client.end();
            return;
        }
        
        const user = userResult.rows[0];
        console.log(`\nFound user: ${user.username} (${user.email})`);
        
        // Delete any existing entry for this API key
        const keyPrefix = 'vibe_prod...';
        await client.query('DELETE FROM api_keys WHERE key_prefix = $1', [keyPrefix]);
        console.log('Cleaned up old entries');
        
        // Insert the API key with correct hash
        const result = await client.query(`
            INSERT INTO api_keys (
                user_id, 
                key_hash, 
                key_prefix, 
                name, 
                is_active,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        `, [
            user.id,
            keyHash,
            keyPrefix,
            'Gateway API Key',
            true
        ]);
        
        console.log('✅ API key created successfully with ID:', result.rows[0].id);
        
        // Verify it was created
        const verify = await client.query(
            'SELECT * FROM api_keys WHERE key_hash = $1',
            [keyHash]
        );
        
        if (verify.rows.length > 0) {
            console.log('✅ Verified: API key exists in database');
        }
        
        // Check permissions
        const permissions = await client.query(
            'SELECT * FROM schema_permissions WHERE user_id = $1',
            [user.id]
        );
        
        console.log('\nUser permissions:');
        if (permissions.rows.length === 0) {
            console.log('  No permissions set');
        } else {
            permissions.rows.forEach(p => {
                console.log(`  - ${p.database_name}.${p.schema_name}: ${p.permission}`);
            });
        }
        
        console.log('\n✅ API key is now properly configured!');
        console.log('The /api/auth/validate and /api/auth/permissions endpoints should work now.');
        
        await client.end();
        
    } catch (error) {
        console.error('Error:', error.message);
        console.error(error.stack);
        await client.end();
    }
}

fixApiKeyWithSalt();