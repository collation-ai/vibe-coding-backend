import asyncpg
import asyncio

async def check_session():
    # Check if the session exists in Azure Table Storage
    # For now, let's just verify the user exists in the database
    
    conn = await asyncpg.connect(
        "postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"
    )
    
    # Check what user the session belongs to
    # The session ID is: 4648fb03-527e-4422-9e35-2d0c937d6865
    # But we can't directly query Azure Table Storage from here
    
    # Let's check if freshwaterapiuser exists and has the right setup
    user = await conn.fetchrow("""
        SELECT id, username, email
        FROM users 
        WHERE username = 'freshwaterapiuser'
    """)
    
    if user:
        print(f"User found: {user['username']}")
        print(f"User ID: {user['id']}")
        
        # Check their permissions
        perms = await conn.fetch("""
            SELECT database_name, schema_name, permission
            FROM schema_permissions
            WHERE user_id = $1
            ORDER BY database_name, schema_name
        """, user['id'])
        
        print("\nPermissions that should be returned:")
        for p in perms:
            print(f"  {p['database_name']}.{p['schema_name']}: {p['permission']}")
    
    await conn.close()

asyncio.run(check_session())
