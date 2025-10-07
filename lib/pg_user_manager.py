"""
PostgreSQL User Manager
Handles creation and management of PostgreSQL database users for Vibe users
"""
import secrets
import string
import asyncpg
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from cryptography.fernet import Fernet
import structlog

from lib.config import settings
from lib.database import db_manager

logger = structlog.get_logger()


class PostgreSQLUserManager:
    """Manages PostgreSQL database users for granular access control"""

    def __init__(self):
        self.fernet = Fernet(settings.encryption_key.encode())

    def generate_pg_credentials(self) -> Dict[str, str]:
        """
        Generate secure PostgreSQL username and password

        Returns:
            {"username": "vibe_user_xxxxx", "password": "..."}
        """
        # Username: vibe_user_<12 random chars>
        # Using lowercase + digits to ensure PostgreSQL compatibility
        random_suffix = "".join(
            secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12)
        )
        username = f"vibe_user_{random_suffix}"

        # Password: 32 character cryptographically secure password
        # Using URL-safe encoding for compatibility
        password = secrets.token_urlsafe(32)

        return {"username": username, "password": password}

    def encrypt(self, value: str) -> str:
        """Encrypt a value using Fernet"""
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a value using Fernet"""
        return self.fernet.decrypt(encrypted_value.encode()).decode()

    def build_connection_string(
        self, base_connection_string: str, pg_username: str, pg_password: str
    ) -> str:
        """
        Build a new connection string with specific user credentials

        Args:
            base_connection_string: Admin connection string
            pg_username: New PostgreSQL username
            pg_password: New PostgreSQL password

        Returns:
            New connection string with user credentials
        """
        # Parse the original connection string
        parsed = urlparse(base_connection_string)

        # Replace username and password
        netloc = f"{pg_username}:{pg_password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"

        # Rebuild connection string
        new_parsed = parsed._replace(netloc=netloc)
        return urlunparse(new_parsed)

    async def create_pg_user(
        self,
        vibe_user_id: str,
        database_name: str,
        admin_connection_string: str,
        created_by_user_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create a PostgreSQL user in the target database

        Args:
            vibe_user_id: Vibe user ID
            database_name: Database name
            admin_connection_string: Admin credentials to create user
            created_by_user_id: Admin user who created this
            notes: Optional notes

        Returns:
            {
                "pg_username": "...",
                "pg_password": "...",
                "connection_string": "..."
            }
        """
        # SECURITY: Prevent creating PostgreSQL users on master_db
        # The master_db contains sensitive user data and should never be accessible to regular users
        if database_name.lower() == "master_db":
            raise ValueError(
                "Cannot create PostgreSQL user on master_db. "
                "The master database contains sensitive system data and is reserved for administrative use only."
            )

        # Generate secure credentials
        creds = self.generate_pg_credentials()
        pg_username = creds["username"]
        pg_password = creds["password"]

        try:
            # Connect to target database with admin credentials
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2, command_timeout=30
            )

            async with admin_pool.acquire() as conn:
                # Check if user already exists
                existing = await conn.fetchval(
                    "SELECT 1 FROM pg_user WHERE usename = $1", pg_username
                )

                if existing:
                    raise ValueError(f"PostgreSQL user {pg_username} already exists")

                # Create PostgreSQL user with LOGIN privilege
                # Escape single quotes in password to prevent SQL injection
                escaped_password = pg_password.replace("'", "''")
                await conn.execute(
                    f"CREATE USER \"{pg_username}\" WITH LOGIN PASSWORD '{escaped_password}'"
                )

                # Grant CONNECT privilege on database
                db_name = urlparse(admin_connection_string).path.lstrip("/")
                await conn.execute(
                    f'GRANT CONNECT ON DATABASE "{db_name}" TO "{pg_username}"'
                )

                await logger.ainfo(
                    "pg_user_created",
                    vibe_user_id=vibe_user_id,
                    pg_username=pg_username,
                    database=database_name,
                )

            await admin_pool.close()

            # Build new connection string with user credentials
            new_connection_string = self.build_connection_string(
                admin_connection_string, pg_username, pg_password
            )

            # Store in master_db
            master_pool = await db_manager.get_master_pool()
            async with master_pool.acquire() as conn:
                # Store PG user credentials
                await conn.execute(
                    """
                    INSERT INTO pg_database_users
                    (vibe_user_id, database_name, pg_username, pg_password_encrypted,
                     connection_string_encrypted, created_by, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    vibe_user_id,
                    database_name,
                    pg_username,
                    self.encrypt(pg_password),
                    self.encrypt(new_connection_string),
                    created_by_user_id,
                    notes,
                )

                # Also create database_assignments entry so user can access the database
                try:
                    await conn.execute(
                        """
                        INSERT INTO database_assignments
                        (user_id, database_name, connection_string_encrypted, is_active)
                        VALUES ($1, $2, $3, true)
                        ON CONFLICT (user_id, database_name) DO UPDATE
                        SET connection_string_encrypted = EXCLUDED.connection_string_encrypted,
                            is_active = true
                        """,
                        vibe_user_id,
                        database_name,
                        self.encrypt(new_connection_string),
                    )
                    await logger.ainfo(
                        "database_assignment_created",
                        vibe_user_id=vibe_user_id,
                        database=database_name,
                    )
                except Exception as assign_error:
                    await logger.awarning(
                        "database_assignment_creation_failed", error=str(assign_error)
                    )

            return {
                "pg_username": pg_username,
                "pg_password": pg_password,
                "connection_string": new_connection_string,
            }

        except Exception as e:
            await logger.aerror(
                "pg_user_creation_failed",
                vibe_user_id=vibe_user_id,
                database=database_name,
                error=str(e),
            )
            raise

    async def get_pg_user_connection(
        self, vibe_user_id: str, database_name: str
    ) -> Optional[str]:
        """
        Get the PostgreSQL connection string for a Vibe user

        Returns:
            Decrypted connection string or None if not found
        """
        master_pool = await db_manager.get_master_pool()
        async with master_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT connection_string_encrypted, is_active
                FROM pg_database_users
                WHERE vibe_user_id = $1 AND database_name = $2
                """,
                vibe_user_id,
                database_name,
            )

            if not row or not row["is_active"]:
                return None

            return self.decrypt(row["connection_string_encrypted"])

    async def get_pg_username(
        self, vibe_user_id: str, database_name: str
    ) -> Optional[str]:
        """Get the PostgreSQL username for a Vibe user"""
        master_pool = await db_manager.get_master_pool()
        async with master_pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT pg_username
                FROM pg_database_users
                WHERE vibe_user_id = $1 AND database_name = $2 AND is_active = true
                """,
                vibe_user_id,
                database_name,
            )

    async def drop_pg_user(
        self, vibe_user_id: str, database_name: str, admin_connection_string: str
    ) -> bool:
        """
        Drop a PostgreSQL user and revoke all privileges

        Args:
            vibe_user_id: Vibe user ID
            database_name: Database name
            admin_connection_string: Admin credentials

        Returns:
            True if successful, False otherwise
        """
        # Get PG username
        pg_username = await self.get_pg_username(vibe_user_id, database_name)
        if not pg_username:
            return False

        try:
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                # Get admin username from connection string
                from urllib.parse import urlparse

                parsed = urlparse(admin_connection_string)
                admin_username = parsed.username

                # Reassign owned objects to admin (prevents dependency errors)
                try:
                    await conn.execute(
                        f'REASSIGN OWNED BY "{pg_username}" TO "{admin_username}"'
                    )
                except Exception as e:
                    await logger.awarning("reassign_owned_failed", error=str(e))

                # Drop owned objects
                try:
                    await conn.execute(f'DROP OWNED BY "{pg_username}"')
                except Exception as e:
                    await logger.awarning("drop_owned_failed", error=str(e))

                # Revoke database privileges
                db_name = parsed.path.lstrip("/")
                try:
                    await conn.execute(
                        f'REVOKE ALL PRIVILEGES ON DATABASE "{db_name}" FROM "{pg_username}"'
                    )
                except Exception as e:
                    await logger.awarning("revoke_db_privileges_failed", error=str(e))

                # Drop user
                await conn.execute(f'DROP USER IF EXISTS "{pg_username}"')

                await logger.ainfo(
                    "pg_user_dropped",
                    vibe_user_id=vibe_user_id,
                    pg_username=pg_username,
                    database=database_name,
                )

            await admin_pool.close()

            # Delete from master_db (hard delete, not soft delete)
            master_pool = await db_manager.get_master_pool()
            async with master_pool.acquire() as conn:
                # Also delete from database_assignments
                await conn.execute(
                    """
                    DELETE FROM database_assignments
                    WHERE user_id = $1 AND database_name = $2
                    """,
                    vibe_user_id,
                    database_name,
                )

                # Delete PG user record
                await conn.execute(
                    """
                    DELETE FROM pg_database_users
                    WHERE vibe_user_id = $1 AND database_name = $2
                    """,
                    vibe_user_id,
                    database_name,
                )

            return True

        except Exception as e:
            await logger.aerror(
                "pg_user_drop_failed",
                vibe_user_id=vibe_user_id,
                pg_username=pg_username,
                error=str(e),
            )
            return False

    async def reset_pg_password(
        self, vibe_user_id: str, database_name: str, admin_connection_string: str
    ) -> Optional[str]:
        """
        Reset PostgreSQL user password

        Returns:
            New password or None if failed
        """
        pg_username = await self.get_pg_username(vibe_user_id, database_name)
        if not pg_username:
            return None

        # Generate new password
        new_password = secrets.token_urlsafe(32)

        try:
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                await conn.execute(
                    f'ALTER USER "{pg_username}" WITH PASSWORD $1', new_password
                )

            await admin_pool.close()

            # Update in master_db
            new_connection_string = self.build_connection_string(
                admin_connection_string, pg_username, new_password
            )

            master_pool = await db_manager.get_master_pool()
            async with master_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE pg_database_users
                    SET pg_password_encrypted = $1,
                        connection_string_encrypted = $2,
                        updated_at = NOW()
                    WHERE vibe_user_id = $3 AND database_name = $4
                    """,
                    self.encrypt(new_password),
                    self.encrypt(new_connection_string),
                    vibe_user_id,
                    database_name,
                )

            await logger.ainfo(
                "pg_password_reset", vibe_user_id=vibe_user_id, pg_username=pg_username
            )

            return new_password

        except Exception as e:
            await logger.aerror(
                "pg_password_reset_failed", vibe_user_id=vibe_user_id, error=str(e)
            )
            return None


# Singleton instance
pg_user_manager = PostgreSQLUserManager()
