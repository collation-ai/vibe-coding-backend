#!/usr/bin/env python3
"""
Database initialization script
Creates master database schema and adds sample data for testing
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.auth import auth_manager
from lib.permissions import Permission

# Load environment variables
load_dotenv()


async def init_database():
    """Initialize the master database with schema and sample data"""
    
    master_db_url = os.getenv('MASTER_DB_URL')
    if not master_db_url:
        print("ERROR: MASTER_DB_URL not found in environment variables")
        return
    
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        print("WARNING: ENCRYPTION_KEY not found, generating a new one...")
        encryption_key = Fernet.generate_key().decode()
        print(f"Generated ENCRYPTION_KEY: {encryption_key}")
        print("Please add this to your .env file")
    
    try:
        # Connect to master database
        print("Connecting to master database...")
        conn = await asyncpg.connect(master_db_url)
        
        # Read and execute the SQL script
        script_path = os.path.join(os.path.dirname(__file__), 'init_db.sql')
        with open(script_path, 'r') as f:
            sql_script = f.read()
        
        print("Creating database schema...")
        await conn.execute(sql_script)
        
        # Create a sample user for testing
        print("Creating sample user...")
        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, organization)
            VALUES ($1, $2)
            ON CONFLICT (email) DO UPDATE SET organization = $2
            RETURNING id
            """,
            "admin@example.com", "Example Corp"
        )
        print(f"Sample user created with ID: {user_id}")
        
        # Generate an API key for the sample user
        print("Generating API key...")
        api_key, key_hash = auth_manager.generate_api_key("dev")
        
        await conn.execute(
            """
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (key_hash) DO NOTHING
            """,
            user_id, key_hash, "vibe_dev", "Development Key"
        )
        print(f"API Key generated: {api_key}")
        print("Save this API key - it cannot be retrieved again!")
        
        # Create sample database assignment
        print("Creating sample database assignment...")
        fernet = Fernet(encryption_key.encode())
        
        # Example connection string - replace with actual
        sample_db_url = os.getenv('SAMPLE_USER_DB_URL', 'postgresql://user:pass@host/user_db_001')
        encrypted_url = fernet.encrypt(sample_db_url.encode()).decode()
        
        await conn.execute(
            """
            INSERT INTO database_assignments (user_id, database_name, connection_string_encrypted)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, database_name) DO UPDATE SET connection_string_encrypted = $3
            """,
            user_id, "user_db_001", encrypted_url
        )
        
        # Grant permissions on public schema
        print("Granting permissions...")
        await conn.execute(
            """
            INSERT INTO schema_permissions (user_id, database_name, schema_name, permission)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, database_name, schema_name) DO UPDATE SET permission = $4
            """,
            user_id, "user_db_001", "public", "read_write"
        )
        
        print("\n" + "="*50)
        print("Database initialization complete!")
        print("="*50)
        print(f"\nTest User Email: admin@example.com")
        print(f"Test User ID: {user_id}")
        print(f"API Key: {api_key}")
        print(f"Database: user_db_001")
        print(f"Schema: public (read_write)")
        print("\nIMPORTANT: Save the API key above - it cannot be retrieved again!")
        print("="*50)
        
        await conn.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(init_database())