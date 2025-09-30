const { Client } = require('pg');

// Test database connection
async function testConnection() {
    console.log('Testing database connection...\n');
    
    const connectionString = process.argv[2];
    
    if (!connectionString) {
        console.log('Usage: node test-connection.js "postgresql://user:pass@host/db?sslmode=require"');
        process.exit(1);
    }
    
    const client = new Client({
        connectionString: connectionString,
        ssl: {
            rejectUnauthorized: false
        }
    });
    
    try {
        console.log('Connecting to database...');
        await client.connect();
        console.log('✅ Connected successfully!\n');
        
        // Check if tables exist
        const tablesQuery = `
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'api_keys', 'schema_permissions', 'database_assignments', 'audit_logs')
            ORDER BY table_name
        `;
        
        const result = await client.query(tablesQuery);
        console.log('📋 Found tables:');
        result.rows.forEach(row => {
            console.log(`  - ${row.table_name}`);
        });
        
        // Check if any users exist
        const usersQuery = `
            SELECT id, username, email, 
                   CASE WHEN password_hash IS NOT NULL THEN '✅ Has password' ELSE '❌ No password' END as has_password
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        `;
        
        const users = await client.query(usersQuery);
        console.log('\n👥 Users in database:');
        if (users.rows.length === 0) {
            console.log('  No users found');
        } else {
            users.rows.forEach(user => {
                console.log(`  - ${user.username || 'NO USERNAME'} (${user.email}) - ${user.has_password}`);
            });
        }
        
        await client.end();
        console.log('\n✅ Database is properly configured!');
        
    } catch (error) {
        console.error('❌ Connection failed:', error.message);
        console.error('\nFull error:', error);
        process.exit(1);
    }
}

testConnection();