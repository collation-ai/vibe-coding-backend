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

        # Always allow read-only access to information_schema
        if (
            schema_name == "information_schema"
            and required_permission == Permission.READ_ONLY
        ):
            await logger.ainfo(
                "permission_granted_information_schema",
                user_id=user_id,
                database=database_name,
                schema=schema_name,
            )
            return True

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

            permissions = [
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

            # Get unique databases from permissions
            databases = list(set(p["database"] for p in permissions))

            # Add information_schema read-only access for each database
            for db in databases:
                if not any(
                    p["database"] == db and p["schema"] == "information_schema"
                    for p in permissions
                ):
                    permissions.append(
                        {
                            "database": db,
                            "schema": "information_schema",
                            "permission": "read_only",
                            "created_at": None,
                            "updated_at": None,
                        }
                    )

            # Sort by database and schema
            permissions.sort(key=lambda x: (x["database"], x["schema"]))

            return permissions

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

            schemas = [
                {"schema": row["schema_name"], "permission": row["permission"]}
                for row in rows
            ]

            # Always include information_schema with read-only access
            # Check if it's not already in the list
            if not any(s["schema"] == "information_schema" for s in schemas):
                schemas.append(
                    {"schema": "information_schema", "permission": "read_only"}
                )
                schemas.sort(key=lambda x: x["schema"])

            return schemas


# Singleton instance
permission_manager = PermissionManager()
