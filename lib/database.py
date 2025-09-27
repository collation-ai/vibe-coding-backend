import asyncpg
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from lib.config import settings
import structlog

logger = structlog.get_logger()


class DatabaseManager:
    def __init__(self):
        self.pools: Dict[str, asyncpg.Pool] = {}
        self.master_pool: Optional[asyncpg.Pool] = None
        self.fernet = Fernet(settings.encryption_key.encode())

    async def get_master_pool(self) -> asyncpg.Pool:
        """Get connection pool for master database"""
        if not self.master_pool:
            self.master_pool = await asyncpg.create_pool(
                settings.master_db_url,
                min_size=settings.min_pool_size,
                max_size=settings.max_pool_size,
                max_queries=50000,
                max_inactive_connection_lifetime=30,
                timeout=10,
                command_timeout=settings.max_query_time_seconds,
                ssl="require" if "azure" in settings.master_db_url else None,
            )
            await logger.ainfo(
                "master_pool_created", url=settings.master_db_url.split("@")[1]
            )
        return self.master_pool

    async def get_user_database_url(self, user_id: str, database_name: str) -> str:
        """Get decrypted database URL for a user's database"""
        pool = await self.get_master_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT connection_string_encrypted
                FROM database_assignments
                WHERE user_id = $1 AND database_name = $2 AND is_active = true
                """,
                user_id,
                database_name,
            )

            if not row:
                raise ValueError(
                    f"Database {database_name} not found for user {user_id}"
                )

            # Decrypt the connection string
            encrypted_url = row["connection_string_encrypted"]
            decrypted_url = self.fernet.decrypt(encrypted_url.encode()).decode()
            return decrypted_url

    async def get_user_pool(self, user_id: str, database_name: str) -> asyncpg.Pool:
        """Get connection pool for a user's database"""
        pool_key = f"{user_id}:{database_name}"

        if pool_key not in self.pools:
            db_url = await self.get_user_database_url(user_id, database_name)

            self.pools[pool_key] = await asyncpg.create_pool(
                db_url,
                min_size=1,  # Minimal for serverless
                max_size=3,  # Limited for Vercel
                max_queries=10000,
                max_inactive_connection_lifetime=20,
                timeout=10,
                command_timeout=settings.max_query_time_seconds,
                ssl="require",
            )
            await logger.ainfo(
                "user_pool_created", user_id=user_id, database=database_name
            )

        return self.pools[pool_key]

    async def execute_query(
        self,
        user_id: str,
        database_name: str,
        query: str,
        params: Optional[List[Any]] = None,
        fetch: bool = True,
        many: bool = True,
    ) -> Any:
        """Execute a query on a user's database"""
        pool = await self.get_user_pool(user_id, database_name)

        async with pool.acquire() as conn:
            try:
                if fetch:
                    if many:
                        result = await conn.fetch(query, *(params or []))
                    else:
                        result = await conn.fetchrow(query, *(params or []))
                    return result
                else:
                    result = await conn.execute(query, *(params or []))
                    # Extract affected rows count from the result string
                    if isinstance(result, str) and " " in result:
                        parts = result.split(" ")
                        if len(parts) >= 2 and parts[-1].isdigit():
                            return int(parts[-1])
                    return result
            except (
                asyncpg.QueryCanceledError,
                asyncpg.IdleInTransactionSessionTimeoutError,
                asyncpg.IdleSessionTimeoutError,
            ) as e:
                await logger.aerror(
                    "query_timeout",
                    user_id=user_id,
                    database=database_name,
                    error=str(e),
                )
                raise
            except Exception as e:
                await logger.aerror(
                    "query_error", user_id=user_id, database=database_name, error=str(e)
                )
                raise

    async def validate_identifier(self, identifier: str) -> bool:
        """Validate that an identifier (schema/table name) is safe"""
        # Only allow alphanumeric, underscore, and dash
        import re

        pattern = r"^[a-zA-Z][a-zA-Z0-9_-]{0,62}$"
        return bool(re.match(pattern, identifier))

    async def close_all(self):
        """Close all connection pools"""
        for pool in self.pools.values():
            await pool.close()
        if self.master_pool:
            await self.master_pool.close()


# Singleton instance
db_manager = DatabaseManager()
