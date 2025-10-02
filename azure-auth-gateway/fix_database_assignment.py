import asyncpg
import asyncio
from cryptography.fernet import Fernet
import base64
import os


async def fix_database_assignment():
    # Create a valid Fernet key (32 bytes, base64 encoded)
    # Use the same key that's in the backend settings
    encryption_key = base64.urlsafe_b64encode(b"zHj3Qm7PbRt5Kw9Nx2Lg4Yv6Fs8Da0Mc")
    fernet = Fernet(encryption_key)

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
        await conn.execute(
            """
            UPDATE database_assignments
            SET connection_string_encrypted = $1
            WHERE user_id = $2 AND database_name = $3
        """,
            encrypted_connection,
            user["id"],
            "master_db",
        )

        print("Updated database assignment for tanmais")
        print(f"User ID: {user['id']}")
        print(f"Database: master_db")
        print("Connection string encrypted and stored")

    await conn.close()


asyncio.run(fix_database_assignment())
