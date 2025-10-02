import asyncpg
import asyncio
from cryptography.fernet import Fernet

async def fix_database_assignment():
    # Use the actual encryption key from Azure settings
    encryption_key = "Q83SKjnvUTBNCD8yEO/AOUd7xh6QWFEUqYKaq1wrtrs="
    fernet = Fernet(encryption_key.encode())
    
    # Connection string for master_db
    connection_string = "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    
    # Encrypt the connection string
    encrypted_connection = fernet.encrypt(connection_string.encode()).decode()
    
    # Connect to master database
    conn = await asyncpg.connect(connection_string)
    
    # Get user ID
    user = await conn.fetchrow("SELECT id FROM users WHERE username = 'tanmais'")
    
    if user:
        # Update the database assignment
        await conn.execute("""
            UPDATE database_assignments
            SET connection_string_encrypted = $1
            WHERE user_id = $2 AND database_name = $3
        """, encrypted_connection, user['id'], 'master_db')
        
        print("Updated database assignment with correct encryption key")
        print(f"User ID: {user['id']}")
        print(f"Database: master_db")
        print("Connection string encrypted with Azure key")
    
    await conn.close()

asyncio.run(fix_database_assignment())
