const { Client } = require('pg');
const bcrypt = require('bcryptjs');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function prompt(question) {
    return new Promise(resolve => {
        rl.question(question, resolve);
    });
}

async function setupUser() {
    console.log('=== Setup User for Vibe Coding Backend ===\n');
    console.log('Database connection string format:');
    console.log('postgresql://username:password@hostname.postgres.database.azure.com:5432/database_name?sslmode=require\n');
    
    // Get database connection string
    const dbUrl = await prompt('Enter Master Database Connection String: ');
    
    const client = new Client({
        connectionString: dbUrl,
        ssl: {
            rejectUnauthorized: false
        }
    });
    
    try {
        await client.connect();
        console.log('Connected to database.\n');
        
        // Get user details
        const username = await prompt('Username: ');
        const email = await prompt('Email: ');
        const password = await prompt('Password: ');
        const organization = await prompt('Organization (optional): ');
        
        // Hash password
        const salt = await bcrypt.genSalt(10);
        const passwordHash = await bcrypt.hash(password, salt);
        
        // Insert user
        const insertUserQuery = `
            INSERT INTO users (username, email, password_hash, organization)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (username) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                organization = EXCLUDED.organization,
                updated_at = NOW()
            RETURNING id, username
        `;
        
        const userResult = await client.query(insertUserQuery, [
            username,
            email,
            passwordHash,
            organization || null
        ]);
        
        const userId = userResult.rows[0].id;
        console.log(`\nUser created/updated: ${username} (${userId})\n`);
        
        // Ask about database assignments
        const addDb = await prompt('Add database assignment? (y/n): ');
        
        if (addDb.toLowerCase() === 'y') {
            const dbName = await prompt('Database name: ');
            const connString = await prompt('Database connection string: ');
            
            // In production, you should encrypt the connection string
            const insertDbQuery = `
                INSERT INTO database_assignments (user_id, database_name, connection_string_encrypted)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, database_name) DO UPDATE SET
                    connection_string_encrypted = EXCLUDED.connection_string_encrypted
            `;
            
            await client.query(insertDbQuery, [userId, dbName, connString]);
            console.log(`Database assignment added: ${dbName}\n`);
            
            // Ask about schema permissions
            const addPerm = await prompt('Add schema permission? (y/n): ');
            
            if (addPerm.toLowerCase() === 'y') {
                const schemaName = await prompt('Schema name (e.g., public): ');
                const permission = await prompt('Permission (read_only/read_write): ');
                
                const insertPermQuery = `
                    INSERT INTO schema_permissions (user_id, database_name, schema_name, permission)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, database_name, schema_name) DO UPDATE SET
                        permission = EXCLUDED.permission,
                        updated_at = NOW()
                `;
                
                await client.query(insertPermQuery, [userId, dbName, schemaName, permission]);
                console.log(`Schema permission added: ${schemaName} (${permission})\n`);
            }
        }
        
        console.log('Setup complete!');
        console.log('\nYou can now login with:');
        console.log(`Username: ${username}`);
        console.log(`Password: [the password you entered]`);
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await client.end();
        rl.close();
    }
}

// Run the setup
setupUser().catch(console.error);