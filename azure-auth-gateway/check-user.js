const { Client } = require('pg');
const bcrypt = require('bcryptjs');

async function checkAndCreateUser() {
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
        
        // Check if user tanmais exists
        const checkQuery = `
            SELECT id, username, email, password_hash 
            FROM users 
            WHERE username = $1 OR email = $1
        `;
        
        const result = await client.query(checkQuery, ['tanmais']);
        
        if (result.rows.length > 0) {
            const user = result.rows[0];
            console.log('User found:');
            console.log('  ID:', user.id);
            console.log('  Username:', user.username || 'NULL');
            console.log('  Email:', user.email);
            console.log('  Has Password:', user.password_hash ? 'Yes' : 'No');
            
            if (!user.password_hash) {
                console.log('\n⚠️  User exists but has no password!');
                console.log('Creating password...');
                
                const salt = await bcrypt.genSalt(10);
                const passwordHash = await bcrypt.hash('Login123#', salt);
                
                await client.query(
                    'UPDATE users SET password_hash = $1, username = $2 WHERE id = $3',
                    [passwordHash, 'tanmais', user.id]
                );
                
                console.log('✅ Password set successfully!');
            } else {
                // Verify the password works
                const validPassword = await bcrypt.compare('Login123#', user.password_hash);
                console.log('\nPassword verification:', validPassword ? '✅ Valid' : '❌ Invalid');
            }
        } else {
            console.log('User "tanmais" not found. Creating...');
            
            const salt = await bcrypt.genSalt(10);
            const passwordHash = await bcrypt.hash('Login123#', salt);
            
            const insertQuery = `
                INSERT INTO users (username, email, password_hash, organization, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, username, email
            `;
            
            const newUser = await client.query(insertQuery, [
                'tanmais',
                'tanmais@vibe-coding.com',
                passwordHash,
                'Vibe Coding',
                true
            ]);
            
            console.log('✅ User created successfully!');
            console.log('  ID:', newUser.rows[0].id);
            console.log('  Username:', newUser.rows[0].username);
            console.log('  Email:', newUser.rows[0].email);
        }
        
        await client.end();
        
    } catch (error) {
        console.error('Error:', error.message);
        await client.end();
    }
}

checkAndCreateUser();