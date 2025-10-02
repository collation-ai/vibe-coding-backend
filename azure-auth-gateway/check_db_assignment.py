import asyncpg
import asyncio


async def check_database_assignment():
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )

    # Check what database assignments exist
    rows = await conn.fetch(
        """
        SELECT u.username, da.database_name, da.is_active
        FROM users u 
        LEFT JOIN database_assignments da ON u.id = da.user_id
        WHERE u.username = 'tanmais'
    """
    )

    print("Database assignments for tanmais:")
    for row in rows:
        print(f"  Database: {row['database_name']}, Active: {row['is_active']}")

    await conn.close()


asyncio.run(check_database_assignment())
