import structlog
from typing import Any, Dict, Optional
from datetime import datetime
import json
from lib.database import db_manager
from lib.config import settings

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class AuditLogger:
    async def log_operation(
        self,
        user_id: str,
        api_key_id: str,
        endpoint: str,
        method: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        operation: Optional[str] = None,
        request_body: Optional[Dict[str, Any]] = None,
        response_status: int = 200,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ):
        """Log an API operation to the audit log"""
        if not settings.enable_audit_logs:
            return

        try:
            pool = await db_manager.get_master_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (
                        user_id, api_key_id, endpoint, method,
                        database_name, schema_name, table_name,
                        operation, request_body, response_status,
                        error_message, execution_time_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    user_id,
                    api_key_id,
                    endpoint,
                    method,
                    database_name,
                    schema_name,
                    table_name,
                    operation,
                    json.dumps(request_body) if request_body else None,
                    response_status,
                    error_message,
                    execution_time_ms,
                )
        except Exception as e:
            # Don't fail the operation if audit logging fails
            logger = structlog.get_logger()
            await logger.aerror("audit_log_failed", error=str(e))

    async def get_user_logs(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list:
        """Retrieve audit logs for a user"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT
                    endpoint, method, database_name, schema_name,
                    table_name, operation, response_status,
                    error_message, execution_time_ms, created_at
                FROM audit_logs
                WHERE user_id = $1
            """
            params = [user_id]

            if start_date:
                query += f" AND created_at >= ${len(params) + 1}"
                params.append(start_date)

            if end_date:
                query += f" AND created_at <= ${len(params) + 1}"
                params.append(end_date)

            query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
            params.extend([limit, offset])

            rows = await conn.fetch(query, *params)

            return [
                {
                    "endpoint": row["endpoint"],
                    "method": row["method"],
                    "database": row["database_name"],
                    "schema": row["schema_name"],
                    "table": row["table_name"],
                    "operation": row["operation"],
                    "status": row["response_status"],
                    "error": row["error_message"],
                    "execution_time_ms": row["execution_time_ms"],
                    "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]


# Singleton instances
logger = structlog.get_logger()
audit_logger = AuditLogger()
