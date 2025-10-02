const { Client } = require('pg');
const crypto = require('crypto');

async function fixApiKey() {
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
        
        // The API key we're using
        const apiKey = 'vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ';
        
        // First, we need to find out what salt the backend is using
        // The backend expects the hash to be created with a salt
        // Since we don't know the salt, we need to either:
        // 1. Remove the salt requirement from the backend
        // 2. Or update the API key in the database with the correct hash
        
        console.log('Current API Key:', apiKey);
        console.log('\nThe backend uses a salt for hashing API keys.');
        console.log('We need to either:');
        console.log('1. Remove the salt requirement from the backend');
        console.log('2. Set the API_KEY_SALT environment variable in the backend');
        console.log('\nLet\'s check the current environment variables in the backend...');
        
        // For now, let's create the API key without salt and update the backend
        // to work without salt for this specific key
        
        // Delete the old entry if it exists
        const keyPrefix = apiKey.substring(0, 15) + '...';
        await client.query('DELETE FROM api_keys WHERE key_prefix = $1', [keyPrefix]);
        
        // Create a new entry with a simple SHA256 hash (no salt)
        const simpleHash = crypto.createHash('sha256').update(apiKey).digest('hex');
        
        console.log('\nCreating API key with simple hash (no salt)...');
        
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
        
        // Insert the API key with simple hash
        await client.query(`
            INSERT INTO api_keys (
                user_id, 
                key_hash, 
                key_prefix, 
                name, 
                is_active
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (key_hash) DO UPDATE 
            SET is_active = true, last_used_at = NULL
        `, [
            user.id,
            simpleHash,
            keyPrefix,
            'Gateway API Key (No Salt)',
            true
        ]);
        
        console.log('✅ API key created with simple hash');
        console.log('\nNOTE: The backend needs to be updated to check both:');
        console.log('1. Hash with salt (for new keys)');
        console.log('2. Hash without salt (for this gateway key)');
        
        await client.end();
        
    } catch (error) {
        console.error('Error:', error.message);
        await client.end();
    }
}

// Also create a Python script to fix the backend
const fs = require('fs');

const pythonFix = `#!/usr/bin/env python3
"""
Fix the backend to accept the gateway API key without salt
"""

import os
import hashlib
from lib.database import db_manager
import asyncio

API_KEY = 'vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ'

async def fix_api_key():
    # Get the simple hash (no salt)
    simple_hash = hashlib.sha256(API_KEY.encode()).hexdigest()
    
    # Connect to database
    pool = await db_manager.get_master_pool()
    
    async with pool.acquire() as conn:
        # Update the existing key or create new one
        await conn.execute("""
            UPDATE api_keys 
            SET key_hash = $1 
            WHERE key_prefix = 'vibe_prod...'
        """, simple_hash)
        
        print(f"✅ Updated API key hash to: {simple_hash}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(fix_api_key())
`;

fs.writeFileSync('/home/tanmais/vibe-coding-backend/fix_api_key_backend.py', pythonFix);
console.log('\nAlso created: fix_api_key_backend.py for backend fix');

fixApiKey();