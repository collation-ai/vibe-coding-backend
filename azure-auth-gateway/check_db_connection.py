import asyncpg
import asyncio
from cryptography.fernet import Fernet


async def check_connection():
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )

    # Get the encrypted connection string
    row = await conn.fetchrow(
        """
        SELECT da.connection_string_encrypted, u.id as user_id
        FROM users u 
        JOIN database_assignments da ON u.id = da.user_id
        WHERE u.username = 'tanmais' AND da.database_name = 'master_db'
    """
    )

    if row:
        print(f"User ID: {row['user_id']}")
        print(
            f"Encrypted connection exists: {bool(row['connection_string_encrypted'])}"
        )

        # Try to decrypt it
        encryption_key = "zHj3Qm7PbRt5Kw9Nx2Lg4Yv6Fs8Da0Mc"
        fernet = Fernet(encryption_key.encode())

        try:
            decrypted = fernet.decrypt(
                row["connection_string_encrypted"].encode()
            ).decode()
            print(f"Decryption successful")
            print(
                f"Connection string points to: {decrypted.split('@')[1] if '@' in decrypted else 'Invalid format'}"
            )
        except Exception as e:
            print(f"Decryption failed: {e}")

    await conn.close()


asyncio.run(check_connection())
