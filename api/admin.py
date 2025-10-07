from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List
from datetime import datetime
import uuid
import bcrypt
from pydantic import BaseModel, EmailStr

from lib.auth import auth_manager
from lib.database import db_manager
from lib.permissions import permission_manager
from lib.config import settings
from lib.pg_user_manager import pg_user_manager
from lib.permission_granter import permission_granter

router = APIRouter()


# Request/Response Models
class CreateUserRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str
    organization: Optional[str] = None


class CreateApiKeyRequest(BaseModel):
    user_id: str
    name: str
    environment: str = "prod"
    expires_in_days: Optional[int] = None


class AssignDatabaseRequest(BaseModel):
    user_id: str
    database_name: str
    connection_string: str


class GrantPermissionRequest(BaseModel):
    user_id: str
    database_name: str
    schema_name: str
    permission: str  # read_only or read_write


class CreatePgUserRequest(BaseModel):
    user_id: str
    database_name: str
    admin_connection_string: str
    notes: Optional[str] = None


class GrantTablePermissionRequest(BaseModel):
    user_id: str
    database_name: str
    admin_connection_string: str
    schema_name: str
    table_name: str
    can_select: bool = False
    can_insert: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_truncate: bool = False
    can_references: bool = False
    can_trigger: bool = False
    column_permissions: Optional[dict] = None


class CreateRlsPolicyRequest(BaseModel):
    user_id: str
    database_name: str
    admin_connection_string: str
    schema_name: str
    table_name: str
    policy_name: str
    policy_type: str  # SELECT, INSERT, UPDATE, DELETE, ALL
    using_expression: str
    with_check_expression: Optional[str] = None
    command_type: str = 'PERMISSIVE'  # PERMISSIVE or RESTRICTIVE
    template_used: Optional[str] = None
    notes: Optional[str] = None


class CreateDatabaseServerRequest(BaseModel):
    server_name: str
    host: str
    port: int = 5432
    admin_username: str
    admin_password: str
    ssl_mode: str = 'require'
    notes: Optional[str] = None


class UpdateDatabaseServerRequest(BaseModel):
    server_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    ssl_mode: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# Admin Authentication Helper
async def verify_admin(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify that the request is from an admin user"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    user_info = await auth_manager.validate_api_key(x_api_key)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user_info


# User Management Endpoints
@router.get("/api/admin/users")
async def list_users(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """List all users"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, email, username, organization, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            """
        )

        users = [dict(row) for row in rows]
        return {"success": True, "data": users}


@router.post("/api/admin/users")
async def create_user(
    request: CreateUserRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Create a new user"""
    await verify_admin(x_api_key)

    # Hash the password
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    username = request.username or request.email

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        try:
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, username, password_hash, organization)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                request.email,
                username,
                password_hash,
                request.organization,
            )

            return {
                "success": True,
                "data": {"user_id": str(user_id), "email": request.email}
            }
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=400, detail="Email or username already exists")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/admin/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Activate a user"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_active = true WHERE id = $1",
            user_id
        )

    return {"success": True, "message": "User activated"}


@router.post("/api/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Deactivate a user"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_active = false WHERE id = $1",
            user_id
        )

    return {"success": True, "message": "User deactivated"}


@router.get("/api/admin/users/{user_id}/databases")
async def get_user_databases(
    user_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Get databases assigned to a user"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT database_name, created_at
            FROM database_assignments
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id
        )

        databases = [dict(row) for row in rows]
        return {"success": True, "data": databases}


# API Key Management Endpoints
@router.get("/api/admin/api-keys")
async def list_api_keys(
    user_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all API keys"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT k.id, k.user_id, k.name, k.key_prefix, k.is_active,
                   k.last_used_at, k.created_at, k.expires_at,
                   u.email as user_email
            FROM api_keys k
            JOIN users u ON k.user_id = u.id
        """

        if user_id:
            query += " WHERE k.user_id = $1"
            rows = await conn.fetch(query + " ORDER BY k.created_at DESC", user_id)
        else:
            rows = await conn.fetch(query + " ORDER BY k.created_at DESC")

        keys = [dict(row) for row in rows]
        return {"success": True, "data": keys}


@router.post("/api/admin/api-keys")
async def create_api_key(
    request: CreateApiKeyRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Generate a new API key for a user"""
    await verify_admin(x_api_key)

    api_key = await auth_manager.create_api_key(
        user_id=request.user_id,
        name=request.name,
        environment=request.environment,
        expires_in_days=request.expires_in_days
    )

    return {
        "success": True,
        "data": {
            "api_key": api_key,
            "message": "Save this key - it cannot be retrieved again!"
        }
    }


@router.post("/api/admin/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Revoke an API key"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1",
            key_id
        )

    return {"success": True, "message": "API key revoked"}


# Database Assignment Endpoints
@router.get("/api/admin/database-assignments")
async def list_database_assignments(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all database assignments"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT da.id, da.user_id, da.database_name, da.created_at,
                   u.email as user_email
            FROM database_assignments da
            JOIN users u ON da.user_id = u.id
            ORDER BY da.created_at DESC
            """
        )

        assignments = [dict(row) for row in rows]
        return {"success": True, "data": assignments}


@router.post("/api/admin/database-assignments")
async def assign_database(
    request: AssignDatabaseRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Assign a database to a user"""
    await verify_admin(x_api_key)

    # SECURITY: Prevent assigning master_db to users
    # The master_db contains sensitive user data and should never be accessible to regular users
    if request.database_name.lower() == 'master_db':
        raise HTTPException(
            status_code=403,
            detail="Cannot assign master_db to users. The master database contains sensitive system data and is reserved for administrative use only."
        )

    # Encrypt the connection string
    from cryptography.fernet import Fernet
    cipher = Fernet(settings.encryption_key.encode())
    encrypted_connection_string = cipher.encrypt(
        request.connection_string.encode()
    ).decode()

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO database_assignments
                (user_id, database_name, connection_string_encrypted)
                VALUES ($1, $2, $3)
                """,
                request.user_id,
                request.database_name,
                encrypted_connection_string,
            )

            return {"success": True, "message": "Database assigned successfully"}
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="User already has access to this database"
                )
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/database-assignments/{assignment_id}")
async def remove_database_assignment(
    assignment_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Remove a database assignment"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM database_assignments WHERE id = $1",
            assignment_id
        )

    return {"success": True, "message": "Database assignment removed"}


# Permission Management Endpoints
@router.get("/api/admin/permissions")
async def list_permissions(
    user_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all schema permissions"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT sp.id, sp.user_id, sp.database_name, sp.schema_name,
                   sp.permission, sp.created_at, sp.updated_at,
                   u.email as user_email
            FROM schema_permissions sp
            JOIN users u ON sp.user_id = u.id
        """

        if user_id:
            query += " WHERE sp.user_id = $1"
            rows = await conn.fetch(query + " ORDER BY sp.created_at DESC", user_id)
        else:
            rows = await conn.fetch(query + " ORDER BY sp.created_at DESC")

        permissions = [dict(row) for row in rows]
        return {"success": True, "data": permissions}


@router.post("/api/admin/permissions")
async def grant_permission(
    request: GrantPermissionRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Grant schema permission to a user"""
    await verify_admin(x_api_key)

    if request.permission not in ["read_only", "read_write"]:
        raise HTTPException(
            status_code=400,
            detail="Permission must be 'read_only' or 'read_write'"
        )

    # SECURITY: Prevent granting permissions on master_db
    # The master_db contains sensitive user data and should never be accessible to regular users
    if request.database_name.lower() == 'master_db':
        raise HTTPException(
            status_code=403,
            detail="Cannot grant permissions on master_db. The master database contains sensitive system data and is reserved for administrative use only."
        )

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        try:
            # First, update the schema_permissions table
            await conn.execute(
                """
                INSERT INTO schema_permissions
                (user_id, database_name, schema_name, permission)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, database_name, schema_name)
                DO UPDATE SET permission = $4, updated_at = NOW()
                """,
                request.user_id,
                request.database_name,
                request.schema_name,
                request.permission,
            )

            # Now, actually grant the PostgreSQL permissions
            # Check if user has a PostgreSQL user for this database
            from lib.pg_user_manager import pg_user_manager
            from lib.permission_granter import permission_granter

            pg_username = await pg_user_manager.get_pg_username(
                request.user_id,
                request.database_name
            )

            if pg_username:
                # Get database connection string
                db_assignment = await conn.fetchrow(
                    """
                    SELECT connection_string_encrypted
                    FROM database_assignments
                    WHERE user_id = $1 AND database_name = $2
                    """,
                    request.user_id,
                    request.database_name
                )

                if not db_assignment:
                    raise HTTPException(
                        status_code=400,
                        detail=f"User does not have access to database {request.database_name}"
                    )

                # Get admin connection string for the database server
                from cryptography.fernet import Fernet
                cipher = Fernet(settings.encryption_key.encode())

                # For now, we'll get the admin connection from database_servers table
                # First, extract the host from user's connection string to find the server
                user_conn_str = cipher.decrypt(
                    db_assignment['connection_string_encrypted'].encode()
                ).decode()

                from urllib.parse import urlparse
                parsed = urlparse(user_conn_str)
                host = parsed.hostname

                # Find the database server
                server = await conn.fetchrow(
                    """
                    SELECT id, host, port, admin_username, admin_password_encrypted, ssl_mode
                    FROM database_servers
                    WHERE host = $1 AND is_active = true
                    LIMIT 1
                    """,
                    host
                )

                if server:
                    # Decrypt admin password
                    admin_password = cipher.decrypt(
                        server['admin_password_encrypted'].encode()
                    ).decode()

                    # Build admin connection string
                    admin_conn_str = (
                        f"postgresql://{server['admin_username']}:{admin_password}@"
                        f"{server['host']}:{server['port']}/{request.database_name}?sslmode={server['ssl_mode']}"
                    )

                    # Map permission level to actual permissions
                    permissions = {
                        'can_select': True,
                        'can_insert': request.permission == 'read_write',
                        'can_update': request.permission == 'read_write',
                        'can_delete': request.permission == 'read_write',
                        'can_truncate': False,
                        'can_references': False,
                        'can_trigger': False,
                        'can_create_table': False,
                        'can_drop_table': False,
                        'can_alter_table': False
                    }

                    # Grant the permissions on the PostgreSQL database
                    await permission_granter.grant_schema_permissions(
                        vibe_user_id=request.user_id,
                        database_name=request.database_name,
                        admin_connection_string=admin_conn_str,
                        schema_name=request.schema_name,
                        permissions=permissions,
                        apply_to_existing=True,
                        apply_to_future=True
                    )

            return {"success": True, "message": "Permission granted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            await logger.aerror("grant_permission_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/permissions/{permission_id}")
async def revoke_permission(
    permission_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Revoke a schema permission"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM schema_permissions WHERE id = $1",
            permission_id
        )

    return {"success": True, "message": "Permission revoked"}


# PostgreSQL User Management Endpoints
@router.get("/api/admin/pg-users")
async def list_pg_users(
    user_id: Optional[str] = None,
    database_name: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List PostgreSQL database users"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT pgu.id, pgu.vibe_user_id, pgu.database_name, pgu.pg_username,
                   pgu.is_active, pgu.created_at, pgu.notes,
                   u.email as user_email
            FROM pg_database_users pgu
            JOIN users u ON pgu.vibe_user_id = u.id
            WHERE 1=1
        """
        params = []

        if user_id:
            params.append(user_id)
            query += f" AND pgu.vibe_user_id = ${len(params)}"

        if database_name:
            params.append(database_name)
            query += f" AND pgu.database_name = ${len(params)}"

        query += " ORDER BY pgu.created_at DESC"

        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)

        pg_users = [dict(row) for row in rows]
        return {"success": True, "data": pg_users}


@router.post("/api/admin/pg-users")
async def create_pg_user(
    request: CreatePgUserRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Create a PostgreSQL user for a Vibe user"""
    admin_info = await verify_admin(x_api_key)

    try:
        result = await pg_user_manager.create_pg_user(
            vibe_user_id=request.user_id,
            database_name=request.database_name,
            admin_connection_string=request.admin_connection_string,
            created_by_user_id=admin_info['user_id'],
            notes=request.notes
        )

        return {
            "success": True,
            "data": {
                "pg_username": result['pg_username'],
                "message": "PostgreSQL user created successfully"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/pg-users/{user_id}/{database_name}")
async def drop_pg_user(
    user_id: str,
    database_name: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Drop a PostgreSQL user - automatically finds admin credentials"""
    await verify_admin(x_api_key)

    try:
        # Get the PG user's connection string to extract host info
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            pg_user_row = await conn.fetchrow(
                """
                SELECT connection_string_encrypted
                FROM pg_database_users
                WHERE vibe_user_id = $1 AND database_name = $2 AND is_active = true
                """,
                user_id,
                database_name
            )

            if not pg_user_row:
                raise HTTPException(status_code=404, detail="PostgreSQL user not found")

            # Decrypt connection string to extract host
            from cryptography.fernet import Fernet
            from lib.config import settings
            from urllib.parse import urlparse

            fernet = Fernet(settings.encryption_key.encode())
            user_conn_string = fernet.decrypt(pg_user_row['connection_string_encrypted'].encode()).decode()
            parsed = urlparse(user_conn_string)
            host = parsed.hostname
            port = parsed.port or 5432

            # Find matching database server
            server_row = await conn.fetchrow(
                """
                SELECT admin_username, admin_password_encrypted, ssl_mode
                FROM database_servers
                WHERE host = $1 AND port = $2 AND is_active = true
                """,
                host,
                port
            )

            if not server_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No database server credentials found for {host}:{port}"
                )

            # Decrypt admin password
            admin_password = fernet.decrypt(server_row['admin_password_encrypted'].encode()).decode()

            # Build admin connection string
            db_name = parsed.path.lstrip('/')
            ssl_mode = server_row['ssl_mode'] or 'require'
            admin_connection_string = f"postgresql://{server_row['admin_username']}:{admin_password}@{host}:{port}/{db_name}?sslmode={ssl_mode}"

        # Now drop the PG user
        success = await pg_user_manager.drop_pg_user(
            vibe_user_id=user_id,
            database_name=database_name,
            admin_connection_string=admin_connection_string
        )

        if success:
            return {"success": True, "message": "PostgreSQL user dropped"}
        else:
            raise HTTPException(status_code=404, detail="PostgreSQL user not found")
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("drop_pg_user_failed", user_id=user_id, database_name=database_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Table-Level Permission Endpoints
@router.get("/api/admin/table-permissions")
async def list_table_permissions(
    user_id: Optional[str] = None,
    database_name: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List table-level permissions"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT tp.id, tp.vibe_user_id, tp.database_name, tp.schema_name,
                   tp.table_name, tp.can_select, tp.can_insert, tp.can_update,
                   tp.can_delete, tp.can_truncate, tp.can_references, tp.can_trigger,
                   tp.column_permissions, tp.created_at, tp.notes,
                   u.email as user_email
            FROM table_permissions tp
            JOIN users u ON tp.vibe_user_id = u.id
            WHERE 1=1
        """
        params = []

        if user_id:
            params.append(user_id)
            query += f" AND tp.vibe_user_id = ${len(params)}"

        if database_name:
            params.append(database_name)
            query += f" AND tp.database_name = ${len(params)}"

        query += " ORDER BY tp.created_at DESC"

        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)

        permissions = [dict(row) for row in rows]
        return {"success": True, "data": permissions}


@router.post("/api/admin/table-permissions")
async def grant_table_permission(
    request: GrantTablePermissionRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Grant table-level permissions"""
    admin_info = await verify_admin(x_api_key)

    # SECURITY: Prevent granting permissions on master_db
    if request.database_name.lower() == 'master_db':
        raise HTTPException(
            status_code=403,
            detail="Cannot grant permissions on master_db. The master database contains sensitive system data and is reserved for administrative use only."
        )

    try:
        permissions = {
            'can_select': request.can_select,
            'can_insert': request.can_insert,
            'can_update': request.can_update,
            'can_delete': request.can_delete,
            'can_truncate': request.can_truncate,
            'can_references': request.can_references,
            'can_trigger': request.can_trigger
        }

        await permission_granter.grant_table_permissions(
            vibe_user_id=request.user_id,
            database_name=request.database_name,
            admin_connection_string=request.admin_connection_string,
            schema_name=request.schema_name,
            table_name=request.table_name,
            permissions=permissions,
            column_permissions=request.column_permissions
        )

        return {"success": True, "message": "Table permissions granted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/table-permissions/{permission_id}")
async def revoke_table_permission(
    permission_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Revoke table-level permissions"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM table_permissions WHERE id = $1",
            permission_id
        )

    return {"success": True, "message": "Table permission revoked"}


# RLS Policy Endpoints
@router.get("/api/admin/rls-policies")
async def list_rls_policies(
    user_id: Optional[str] = None,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List RLS policies"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT rp.id, rp.vibe_user_id, rp.database_name, rp.schema_name,
                   rp.table_name, rp.policy_name, rp.policy_type, rp.command_type,
                   rp.using_expression, rp.with_check_expression, rp.is_active,
                   rp.template_used, rp.notes, rp.created_at,
                   u.email as user_email
            FROM rls_policies rp
            JOIN users u ON rp.vibe_user_id = u.id
            WHERE rp.is_active = true
        """
        params = []

        if user_id:
            params.append(user_id)
            query += f" AND rp.vibe_user_id = ${len(params)}"

        if database_name:
            params.append(database_name)
            query += f" AND rp.database_name = ${len(params)}"

        if table_name:
            params.append(table_name)
            query += f" AND rp.table_name = ${len(params)}"

        query += " ORDER BY rp.created_at DESC"

        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)

        policies = [dict(row) for row in rows]
        return {"success": True, "data": policies}


@router.post("/api/admin/rls-policies")
async def create_rls_policy(
    request: CreateRlsPolicyRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Create an RLS policy"""
    admin_info = await verify_admin(x_api_key)

    # SECURITY: Prevent creating RLS policies on master_db
    if request.database_name.lower() == 'master_db':
        raise HTTPException(
            status_code=403,
            detail="Cannot create RLS policies on master_db. The master database contains sensitive system data and is reserved for administrative use only."
        )

    try:
        await permission_granter.create_rls_policy(
            vibe_user_id=request.user_id,
            database_name=request.database_name,
            admin_connection_string=request.admin_connection_string,
            schema_name=request.schema_name,
            table_name=request.table_name,
            policy_name=request.policy_name,
            policy_type=request.policy_type,
            using_expression=request.using_expression,
            with_check_expression=request.with_check_expression,
            command_type=request.command_type,
            template_used=request.template_used,
            notes=request.notes
        )

        return {"success": True, "message": "RLS policy created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/rls-policies/{policy_id}")
async def drop_rls_policy(
    policy_id: str,
    admin_connection_string: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Drop an RLS policy"""
    await verify_admin(x_api_key)

    try:
        success = await permission_granter.drop_rls_policy(
            policy_id=policy_id,
            admin_connection_string=admin_connection_string
        )

        if success:
            return {"success": True, "message": "RLS policy dropped"}
        else:
            raise HTTPException(status_code=404, detail="RLS policy not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# RLS Policy Templates
@router.get("/api/admin/rls-templates")
async def list_rls_templates(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List available RLS policy templates"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, template_name, description, policy_type,
                   using_expression_template, with_check_expression_template,
                   required_columns, example_usage
            FROM rls_policy_templates
            WHERE is_active = true
            ORDER BY template_name
            """
        )

        templates = [dict(row) for row in rows]
        return {"success": True, "data": templates}


# Database Server Credentials Management
@router.get("/api/admin/database-servers")
async def list_database_servers(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all database servers (credentials hidden)"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, server_name, host, port, admin_username,
                   ssl_mode, is_active, created_at, updated_at, notes
            FROM database_servers
            WHERE is_active = true
            ORDER BY server_name
            """
        )

        servers = [dict(row) for row in rows]
        return {"success": True, "data": servers}


@router.post("/api/admin/database-servers")
async def create_database_server(
    request: CreateDatabaseServerRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Create a new database server configuration"""
    await verify_admin(x_api_key)

    # Encrypt the admin password
    from cryptography.fernet import Fernet
    cipher = Fernet(settings.encryption_key.encode())
    encrypted_password = cipher.encrypt(request.admin_password.encode()).decode()

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        try:
            server_id = await conn.fetchval(
                """
                INSERT INTO database_servers
                (server_name, host, port, admin_username, admin_password_encrypted,
                 ssl_mode, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                request.server_name,
                request.host,
                request.port,
                request.admin_username,
                encrypted_password,
                request.ssl_mode,
                request.notes
            )

            return {
                "success": True,
                "data": {
                    "server_id": str(server_id),
                    "server_name": request.server_name
                }
            }
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="Server name already exists"
                )
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/admin/database-servers/{server_id}/databases")
async def list_databases_on_server(
    server_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all databases on a database server"""
    await verify_admin(x_api_key)

    import asyncpg
    from cryptography.fernet import Fernet, InvalidToken

    try:
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT host, port, admin_username, admin_password_encrypted, ssl_mode
                FROM database_servers
                WHERE id = $1 AND is_active = true
                """,
                server_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Database server not found")

            # Decrypt password
            try:
                cipher = Fernet(settings.encryption_key.encode())
                admin_password = cipher.decrypt(row['admin_password_encrypted'].encode()).decode()
            except InvalidToken:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to decrypt database credentials. The encryption key may have changed. Please re-save the database server credentials."
                )

        # Connect to postgres database to list all databases
        connection_string = (
            f"postgresql://{row['admin_username']}:{admin_password}@"
            f"{row['host']}:{row['port']}/postgres?sslmode={row['ssl_mode']}"
        )

        db_conn = await asyncpg.connect(connection_string)

        # Query all databases except system databases
        databases = await db_conn.fetch(
            """
            SELECT datname
            FROM pg_database
            WHERE datistemplate = false
            AND datname NOT IN ('postgres', 'template0', 'template1', 'azure_maintenance')
            ORDER BY datname
            """
        )

        await db_conn.close()

        database_list = [db['datname'] for db in databases]

        return {
            "success": True,
            "data": database_list
        }
    except HTTPException:
        raise
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        await logger.aerror(
            "failed_to_list_databases",
            server_id=server_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to database server: {str(e)}"
        )


@router.get("/api/admin/database-servers/{server_id}/connection-string")
async def get_database_server_connection_string(
    server_id: str,
    database_name: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Get the full admin connection string for a database server"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT host, port, admin_username, admin_password_encrypted, ssl_mode
            FROM database_servers
            WHERE id = $1 AND is_active = true
            """,
            server_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Database server not found")

        # Decrypt password
        from cryptography.fernet import Fernet
        cipher = Fernet(settings.encryption_key.encode())
        admin_password = cipher.decrypt(row['admin_password_encrypted'].encode()).decode()

        # Build connection string
        connection_string = (
            f"postgresql://{row['admin_username']}:{admin_password}@"
            f"{row['host']}:{row['port']}/{database_name}?sslmode={row['ssl_mode']}"
        )

        return {
            "success": True,
            "data": {
                "connection_string": connection_string,
                "host": row['host'],
                "port": row['port'],
                "username": row['admin_username']
            }
        }


@router.put("/api/admin/database-servers/{server_id}")
async def update_database_server(
    server_id: str,
    request: UpdateDatabaseServerRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Update database server configuration"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        # Build dynamic update query
        updates = []
        params = [server_id]
        param_count = 1

        if request.server_name is not None:
            param_count += 1
            updates.append(f"server_name = ${param_count}")
            params.append(request.server_name)

        if request.host is not None:
            param_count += 1
            updates.append(f"host = ${param_count}")
            params.append(request.host)

        if request.port is not None:
            param_count += 1
            updates.append(f"port = ${param_count}")
            params.append(request.port)

        if request.admin_username is not None:
            param_count += 1
            updates.append(f"admin_username = ${param_count}")
            params.append(request.admin_username)

        if request.admin_password is not None:
            from cryptography.fernet import Fernet
            cipher = Fernet(settings.encryption_key.encode())
            encrypted_password = cipher.encrypt(request.admin_password.encode()).decode()
            param_count += 1
            updates.append(f"admin_password_encrypted = ${param_count}")
            params.append(encrypted_password)

        if request.ssl_mode is not None:
            param_count += 1
            updates.append(f"ssl_mode = ${param_count}")
            params.append(request.ssl_mode)

        if request.notes is not None:
            param_count += 1
            updates.append(f"notes = ${param_count}")
            params.append(request.notes)

        if request.is_active is not None:
            param_count += 1
            updates.append(f"is_active = ${param_count}")
            params.append(request.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        query = f"UPDATE database_servers SET {', '.join(updates)} WHERE id = $1"

        await conn.execute(query, *params)

        return {"success": True, "message": "Database server updated"}


@router.delete("/api/admin/database-servers/{server_id}")
async def delete_database_server(
    server_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Delete a database server completely"""
    await verify_admin(x_api_key)

    pool = await db_manager.get_master_pool()
    async with pool.acquire() as conn:
        # Actually delete the server record (not soft delete)
        await conn.execute(
            "DELETE FROM database_servers WHERE id = $1",
            server_id
        )

    return {"success": True, "message": "Database server deleted"}
