from typing import List, Dict, Any
from enum import Enum
import structlog
from lib.database import db_manager

logger = structlog.get_logger()


class Permission(Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class PermissionManager:
    async def check_permission(
        self, user_id: str, database_name: str, schema_name: str, operation: str
    ) -> bool:
        """Check if user has permission for an operation on a schema"""
        required_permission = self._get_required_permission(operation)

        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT permission
                FROM schema_permissions
                WHERE user_id = $1
                AND database_name = $2
                AND schema_name = $3
                """,
                user_id,
                database_name,
                schema_name,
            )

            if not row:
                await logger.ainfo(
                    "permission_denied_no_access",
                    user_id=user_id,
                    database=database_name,
                    schema=schema_name,
                )
                return False

            user_permission = Permission(row["permission"])

            # READ_WRITE permission allows all operations
            if user_permission == Permission.READ_WRITE:
                return True

            # READ_ONLY only allows read operations
            if (
                user_permission == Permission.READ_ONLY
                and required_permission == Permission.READ_ONLY
            ):
                return True

            await logger.ainfo(
                "permission_denied_insufficient",
                user_id=user_id,
                database=database_name,
                schema=schema_name,
                required=required_permission.value,
                user_has=user_permission.value,
            )
            return False

    def _get_required_permission(self, operation: str) -> Permission:
        """Determine required permission level for an operation"""
        read_operations = [
            "select",
            "read",
            "get",
            "list",
            "describe",
            "show",
            "explain",
        ]

        operation_lower = operation.lower()

        # Check if it's a read operation
        if any(op in operation_lower for op in read_operations):
            return Permission.READ_ONLY

        # Everything else requires write permission
        return Permission.READ_WRITE

    async def get_user_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all permissions for a user"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    database_name,
                    schema_name,
                    permission,
                    created_at,
                    updated_at
                FROM schema_permissions
                WHERE user_id = $1
                ORDER BY database_name, schema_name
                """,
                user_id,
            )

            return [
                {
                    "database": row["database_name"],
                    "schema": row["schema_name"],
                    "permission": row["permission"],
                    "created_at": row["created_at"].isoformat()
                    if row["created_at"]
                    else None,
                    "updated_at": row["updated_at"].isoformat()
                    if row["updated_at"]
                    else None,
                }
                for row in rows
            ]

    async def grant_permission(
        self, user_id: str, database_name: str, schema_name: str, permission: Permission
    ) -> bool:
        """Grant or update permission for a user on a schema"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO schema_permissions
                (user_id, database_name, schema_name, permission)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, database_name, schema_name)
                DO UPDATE SET
                    permission = $4,
                    updated_at = NOW()
                """,
                user_id,
                database_name,
                schema_name,
                permission.value,
            )

            await logger.ainfo(
                "permission_granted",
                user_id=user_id,
                database=database_name,
                schema=schema_name,
                permission=permission.value,
            )
            return True

    async def revoke_permission(
        self, user_id: str, database_name: str, schema_name: str
    ) -> bool:
        """Revoke permission for a user on a schema"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM schema_permissions
                WHERE user_id = $1
                AND database_name = $2
                AND schema_name = $3
                """,
                user_id,
                database_name,
                schema_name,
            )

            if "DELETE 1" in str(result):
                await logger.ainfo(
                    "permission_revoked",
                    user_id=user_id,
                    database=database_name,
                    schema=schema_name,
                )
                return True
            return False

    async def get_accessible_databases(self, user_id: str) -> List[str]:
        """Get list of databases accessible to a user"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT database_name
                FROM database_assignments
                WHERE user_id = $1
                ORDER BY database_name
                """,
                user_id,
            )

            return [row["database_name"] for row in rows]

    async def get_accessible_schemas(
        self, user_id: str, database_name: str
    ) -> List[Dict[str, str]]:
        """Get list of schemas accessible to a user in a database"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT schema_name, permission
                FROM schema_permissions
                WHERE user_id = $1 AND database_name = $2
                ORDER BY schema_name
                """,
                user_id,
                database_name,
            )

            return [
                {"schema": row["schema_name"], "permission": row["permission"]}
                for row in rows
            ]


# Singleton instance
permission_manager = PermissionManager()
