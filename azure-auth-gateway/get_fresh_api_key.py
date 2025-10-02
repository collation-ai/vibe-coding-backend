import asyncpg
import asyncio


async def get_api_key():
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )

    # Get API key info for freshwaterapiuser
    row = await conn.fetchrow(
        """
        SELECT ak.key_prefix, ak.name, u.username, u.id as user_id
        FROM users u
        JOIN api_keys ak ON u.id = ak.user_id
        WHERE u.username = 'freshwaterapiuser' AND ak.is_active = true
        LIMIT 1
    """
    )

    if row:
        print(f"User: {row['username']}")
        print(f"User ID: {row['user_id']}")
        print(f"API Key prefix: {row['key_prefix']}")
        print(f"API Key name: {row['name']}")
        print("\nNote: Full API key can only be known when created.")
        print("If you don't have it, you'll need to generate a new one.")
    else:
        print("No active API key found for freshwaterapiuser")

    await conn.close()


asyncio.run(get_api_key())
