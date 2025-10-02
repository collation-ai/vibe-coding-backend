const { Client } = require('pg');
const crypto = require('crypto');

async function setupApiKey() {
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
        
        // The API key we're using in the gateway
        const apiKey = 'vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ';
        const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');
        const keyPrefix = apiKey.substring(0, 15) + '...';
        
        console.log('Setting up API key:', keyPrefix);
        
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
        console.log(`Found user: ${user.username} (${user.email})`);
        
        // Check if key already exists
        const existingKey = await client.query(
            'SELECT id FROM api_keys WHERE key_hash = $1',
            [keyHash]
        );
        
        if (existingKey.rows.length > 0) {
            console.log('✅ API key already exists');
        } else {
            // Create the API key
            console.log('\nCreating API key...');
            await client.query(`
                INSERT INTO api_keys (
                    user_id, 
                    key_hash, 
                    key_prefix, 
                    name, 
                    is_active
                ) VALUES ($1, $2, $3, $4, $5)
            `, [
                user.id,
                keyHash,
                keyPrefix,
                'Gateway API Key',
                true
            ]);
            console.log('✅ API key created');
        }
        
        // Check database assignments
        const dbAssignments = await client.query(
            'SELECT database_name FROM database_assignments WHERE user_id = $1',
            [user.id]
        );
        
        console.log('\nDatabase assignments:');
        if (dbAssignments.rows.length === 0) {
            console.log('  No databases assigned');
            
            // Assign master_db
            console.log('\nAssigning master_db to user...');
            const encryptedConnString = Buffer.from(connectionString).toString('base64');
            
            await client.query(`
                INSERT INTO database_assignments (
                    user_id, 
                    database_name, 
                    connection_string_encrypted
                ) VALUES ($1, $2, $3)
                ON CONFLICT (user_id, database_name) DO NOTHING
            `, [user.id, 'master_db', encryptedConnString]);
            
            console.log('✅ Database assigned');
        } else {
            dbAssignments.rows.forEach(db => {
                console.log(`  - ${db.database_name}`);
            });
        }
        
        // Check schema permissions
        const permissions = await client.query(
            'SELECT database_name, schema_name, permission FROM schema_permissions WHERE user_id = $1',
            [user.id]
        );
        
        console.log('\nSchema permissions:');
        if (permissions.rows.length === 0) {
            console.log('  No permissions set');
            
            // Grant permissions on public schema
            console.log('\nGranting read_write permission on public schema...');
            await client.query(`
                INSERT INTO schema_permissions (
                    user_id, 
                    database_name, 
                    schema_name, 
                    permission
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, database_name, schema_name) DO UPDATE SET permission = $4
            `, [user.id, 'master_db', 'public', 'read_write']);
            
            // Also grant read-only access to information_schema
            await client.query(`
                INSERT INTO schema_permissions (
                    user_id, 
                    database_name, 
                    schema_name, 
                    permission
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, database_name, schema_name) DO UPDATE SET permission = $4
            `, [user.id, 'master_db', 'information_schema', 'read_only']);
            
            console.log('✅ Permissions granted');
        } else {
            permissions.rows.forEach(perm => {
                console.log(`  - ${perm.database_name}.${perm.schema_name}: ${perm.permission}`);
            });
        }
        
        console.log('\n✅ API key setup complete!');
        console.log('\nThe API key is now properly configured in the database.');
        console.log('The /api/auth/permissions endpoint should now work.');
        
        await client.end();
        
    } catch (error) {
        console.error('Error:', error.message);
        console.error(error.stack);
        await client.end();
    }
}

setupApiKey();