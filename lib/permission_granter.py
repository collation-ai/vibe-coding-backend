"""
Permission Granter
Handles granting and revoking permissions at schema, table, and row levels
"""
import asyncpg
from typing import Dict, List, Optional
import structlog

from lib.database import db_manager
from lib.pg_user_manager import pg_user_manager

logger = structlog.get_logger()


class PermissionGranter:
    """Manages PostgreSQL permissions at schema, table, and row levels"""

    def _validate_identifier(self, identifier: str) -> str:
        """
        Validate PostgreSQL identifier (schema, table, column names)
        Prevents SQL injection
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Remove dangerous characters
        if any(char in identifier for char in [";", "--", "/*", "*/", "\x00"]):
            raise ValueError(f"Invalid identifier: {identifier}")

        # PostgreSQL identifiers max 63 chars
        if len(identifier) > 63:
            raise ValueError(f"Identifier too long: {identifier}")

        return identifier

    async def grant_schema_permissions(
        self,
        vibe_user_id: str,
        database_name: str,
        admin_connection_string: str,
        schema_name: str,
        permissions: Dict[str, bool],
        apply_to_existing: bool = True,
        apply_to_future: bool = True,
    ) -> bool:
        """
        Grant schema-level permissions to a PostgreSQL user

        Args:
            vibe_user_id: Vibe user ID
            database_name: Database name
            admin_connection_string: Admin credentials
            schema_name: Schema name
            permissions: Dict with can_select, can_insert, can_update,
                can_delete, can_create_table, etc.
            apply_to_existing: Apply to existing tables
            apply_to_future: Apply to future tables

        Returns:
            True if successful
        """
        # Validate inputs
        schema_name = self._validate_identifier(schema_name)

        # Get PostgreSQL username for this Vibe user
        pg_username = await pg_user_manager.get_pg_username(vibe_user_id, database_name)
        if not pg_username:
            raise ValueError(f"No PostgreSQL user found for Vibe user {vibe_user_id}")

        try:
            # Connect with admin credentials
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                # Grant USAGE on schema (required for any access)
                await conn.execute(
                    f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{pg_username}"'
                )

                # Build table permission list
                table_perms = []
                if permissions.get("can_select"):
                    table_perms.append("SELECT")
                if permissions.get("can_insert"):
                    table_perms.append("INSERT")
                if permissions.get("can_update"):
                    table_perms.append("UPDATE")
                if permissions.get("can_delete"):
                    table_perms.append("DELETE")
                if permissions.get("can_truncate"):
                    table_perms.append("TRUNCATE")
                if permissions.get("can_references"):
                    table_perms.append("REFERENCES")
                if permissions.get("can_trigger"):
                    table_perms.append("TRIGGER")

                if table_perms and apply_to_existing:
                    perm_str = ", ".join(table_perms)
                    await conn.execute(
                        f'GRANT {perm_str} ON ALL TABLES IN SCHEMA '
                        f'"{schema_name}" TO "{pg_username}"'
                    )

                if table_perms and apply_to_future:
                    perm_str = ", ".join(table_perms)
                    await conn.execute(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" '
                        f'GRANT {perm_str} ON TABLES TO "{pg_username}"'
                    )

                # Grant sequence permissions for SERIAL columns
                if permissions.get("can_insert") or permissions.get("can_update"):
                    if apply_to_existing:
                        await conn.execute(
                            f'GRANT USAGE, SELECT ON ALL SEQUENCES '
                            f'IN SCHEMA "{schema_name}" TO "{pg_username}"'
                        )
                    if apply_to_future:
                        await conn.execute(
                            f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" '
                            f'GRANT USAGE, SELECT ON SEQUENCES TO "{pg_username}"'
                        )

                # DDL permissions
                if permissions.get("can_create_table"):
                    await conn.execute(
                        f'GRANT CREATE ON SCHEMA "{schema_name}" TO "{pg_username}"'
                    )

                await logger.ainfo(
                    "schema_permissions_granted",
                    vibe_user_id=vibe_user_id,
                    pg_username=pg_username,
                    schema=schema_name,
                    permissions=permissions,
                )

            await admin_pool.close()
            return True

        except Exception as e:
            await logger.aerror(
                "grant_schema_permissions_failed",
                vibe_user_id=vibe_user_id,
                schema=schema_name,
                error=str(e),
            )
            raise

    async def grant_table_permissions(
        self,
        vibe_user_id: str,
        database_name: str,
        admin_connection_string: str,
        schema_name: str,
        table_name: str,
        permissions: Dict[str, bool],
        column_permissions: Optional[Dict[str, List[str]]] = None,
    ) -> bool:
        """
        Grant table-level permissions

        Args:
            vibe_user_id: Vibe user ID
            database_name: Database name
            admin_connection_string: Admin credentials
            schema_name: Schema name
            table_name: Table name
            permissions: Dict with can_select, can_insert, can_update,
                can_delete
            column_permissions: Optional dict like
                {"col1": ["SELECT"], "col2": ["SELECT", "UPDATE"]}

        Returns:
            True if successful
        """
        schema_name = self._validate_identifier(schema_name)
        table_name = self._validate_identifier(table_name)

        pg_username = await pg_user_manager.get_pg_username(vibe_user_id, database_name)
        if not pg_username:
            raise ValueError(f"No PostgreSQL user found for Vibe user {vibe_user_id}")

        try:
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                # Grant USAGE on schema first
                await conn.execute(
                    f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{pg_username}"'
                )

                # Build permission list
                perms = []
                if permissions.get("can_select"):
                    perms.append("SELECT")
                if permissions.get("can_insert"):
                    perms.append("INSERT")
                if permissions.get("can_update"):
                    perms.append("UPDATE")
                if permissions.get("can_delete"):
                    perms.append("DELETE")
                if permissions.get("can_truncate"):
                    perms.append("TRUNCATE")
                if permissions.get("can_references"):
                    perms.append("REFERENCES")
                if permissions.get("can_trigger"):
                    perms.append("TRIGGER")

                # Grant table-level permissions
                if perms:
                    perm_str = ", ".join(perms)
                    await conn.execute(
                        f'GRANT {perm_str} ON "{schema_name}".'
                        f'"{table_name}" TO "{pg_username}"'
                    )

                # Grant column-level permissions if specified
                if column_permissions:
                    for column, col_perms in column_permissions.items():
                        column = self._validate_identifier(column)
                        col_perm_str = ", ".join(col_perms)
                        await conn.execute(
                            f'GRANT {col_perm_str} ({column}) ON '
                            f'"{schema_name}"."{table_name}" TO "{pg_username}"'
                        )

                await logger.ainfo(
                    "table_permissions_granted",
                    vibe_user_id=vibe_user_id,
                    pg_username=pg_username,
                    table=f"{schema_name}.{table_name}",
                    permissions=permissions,
                )

            await admin_pool.close()

            # Store in table_permissions table
            master_pool = await db_manager.get_master_pool()
            async with master_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO table_permissions
                    (vibe_user_id, database_name, schema_name, table_name,
                     can_select, can_insert, can_update, can_delete, can_truncate,
                     can_references, can_trigger, column_permissions)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (vibe_user_id, database_name, schema_name, table_name)
                    DO UPDATE SET
                        can_select = $5,
                        can_insert = $6,
                        can_update = $7,
                        can_delete = $8,
                        can_truncate = $9,
                        can_references = $10,
                        can_trigger = $11,
                        column_permissions = $12,
                        updated_at = NOW()
                    """,
                    vibe_user_id,
                    database_name,
                    schema_name,
                    table_name,
                    permissions.get("can_select", False),
                    permissions.get("can_insert", False),
                    permissions.get("can_update", False),
                    permissions.get("can_delete", False),
                    permissions.get("can_truncate", False),
                    permissions.get("can_references", False),
                    permissions.get("can_trigger", False),
                    column_permissions,
                )

            return True

        except Exception as e:
            await logger.aerror(
                "grant_table_permissions_failed",
                vibe_user_id=vibe_user_id,
                table=f"{schema_name}.{table_name}",
                error=str(e),
            )
            raise

    async def create_rls_policy(
        self,
        vibe_user_id: str,
        database_name: str,
        admin_connection_string: str,
        schema_name: str,
        table_name: str,
        policy_name: str,
        policy_type: str,  # SELECT, INSERT, UPDATE, DELETE, ALL
        using_expression: str,
        with_check_expression: Optional[str] = None,
        command_type: str = "PERMISSIVE",  # PERMISSIVE or RESTRICTIVE
        template_used: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Create Row-Level Security policy

        Args:
            vibe_user_id: Vibe user ID
            database_name: Database name
            admin_connection_string: Admin credentials
            schema_name: Schema name
            table_name: Table name
            policy_name: Unique policy name
            policy_type: SELECT, INSERT, UPDATE, DELETE, or ALL
            using_expression: SQL expression for USING clause
            with_check_expression: Optional SQL expression for WITH CHECK clause
            command_type: PERMISSIVE or RESTRICTIVE
            template_used: Name of template if used
            notes: Optional notes

        Returns:
            True if successful
        """
        schema_name = self._validate_identifier(schema_name)
        table_name = self._validate_identifier(table_name)
        policy_name = self._validate_identifier(policy_name)

        pg_username = await pg_user_manager.get_pg_username(vibe_user_id, database_name)
        if not pg_username:
            raise ValueError(f"No PostgreSQL user found for Vibe user {vibe_user_id}")

        if policy_type not in ["SELECT", "INSERT", "UPDATE", "DELETE", "ALL"]:
            raise ValueError(f"Invalid policy type: {policy_type}")

        if command_type not in ["PERMISSIVE", "RESTRICTIVE"]:
            raise ValueError(f"Invalid command type: {command_type}")

        try:
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                # Enable RLS on table
                await conn.execute(
                    f'ALTER TABLE "{schema_name}"."{table_name}" ENABLE ROW LEVEL SECURITY'
                )

                # Build policy SQL
                policy_sql = (
                    f'CREATE POLICY "{policy_name}" ON "{schema_name}"."{table_name}"'
                )
                policy_sql += f" AS {command_type}"
                policy_sql += f" FOR {policy_type}"
                policy_sql += f' TO "{pg_username}"'

                if using_expression:
                    policy_sql += f" USING ({using_expression})"

                if with_check_expression and policy_type in ["INSERT", "UPDATE", "ALL"]:
                    policy_sql += f" WITH CHECK ({with_check_expression})"

                await conn.execute(policy_sql)

                await logger.ainfo(
                    "rls_policy_created",
                    vibe_user_id=vibe_user_id,
                    pg_username=pg_username,
                    table=f"{schema_name}.{table_name}",
                    policy=policy_name,
                )

            await admin_pool.close()

            # Store in rls_policies table
            master_pool = await db_manager.get_master_pool()
            async with master_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO rls_policies
                    (vibe_user_id, database_name, schema_name, table_name, policy_name,
                     policy_type, command_type, using_expression, with_check_expression,
                     template_used, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    vibe_user_id,
                    database_name,
                    schema_name,
                    table_name,
                    policy_name,
                    policy_type,
                    command_type,
                    using_expression,
                    with_check_expression,
                    template_used,
                    notes,
                )

            return True

        except Exception as e:
            await logger.aerror(
                "create_rls_policy_failed",
                vibe_user_id=vibe_user_id,
                table=f"{schema_name}.{table_name}",
                policy=policy_name,
                error=str(e),
            )
            raise

    async def drop_rls_policy(
        self, policy_id: str, admin_connection_string: str
    ) -> bool:
        """Drop an RLS policy"""
        master_pool = await db_manager.get_master_pool()
        async with master_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT database_name, schema_name, table_name, policy_name
                FROM rls_policies
                WHERE id = $1 AND is_active = true
                """,
                policy_id,
            )

            if not row:
                return False

        schema_name = self._validate_identifier(row["schema_name"])
        table_name = self._validate_identifier(row["table_name"])
        policy_name = self._validate_identifier(row["policy_name"])

        try:
            admin_pool = await asyncpg.create_pool(
                admin_connection_string, min_size=1, max_size=2
            )

            async with admin_pool.acquire() as conn:
                await conn.execute(
                    f'DROP POLICY IF EXISTS "{policy_name}" ON "{schema_name}"."{table_name}"'
                )

            await admin_pool.close()

            # Mark as inactive
            async with master_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE rls_policies
                    SET is_active = false, updated_at = NOW()
                    WHERE id = $1
                    """,
                    policy_id,
                )

            return True

        except Exception as e:
            await logger.aerror(
                "drop_rls_policy_failed", policy_id=policy_id, error=str(e)
            )
            return False


# Singleton instance
permission_granter = PermissionGranter()
