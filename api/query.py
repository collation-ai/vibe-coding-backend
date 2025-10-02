from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Any
import asyncio
import time
from datetime import datetime
import uuid
import re
from lib.auth import auth_manager
from lib.permissions import permission_manager
from lib.database import db_manager
from lib.logging import audit_logger, logger
from schemas.requests import RawQueryRequest
from schemas.responses import (
    SuccessResponse,
    ErrorResponse,
    MetadataResponse,
    ErrorDetail,
)

app = FastAPI()


def process_query_params(params: Optional[List[Any]]) -> List[Any]:
    """
    Process query parameters to convert them to appropriate Python types.
    All parameters must include type information.
    """
    if not params:
        return []

    processed_params = []

    for i, param in enumerate(params):
        # Handle both dict and Pydantic model instances
        if hasattr(param, "value") and hasattr(param, "type"):
            # It's a Pydantic model
            value = param.value
            param_type = param.type.lower()
        elif isinstance(param, dict) and "value" in param and "type" in param:
            # It's a dict
            value = param["value"]
            param_type = param["type"].lower()
        else:
            raise ValueError(f"Parameter {i+1} must have 'value' and 'type' fields")

        try:
            if param_type in ("date", "datetime.date"):
                # Convert to date
                if isinstance(value, str):
                    if len(value) == 10:  # YYYY-MM-DD format
                        processed_params.append(
                            datetime.strptime(value, "%Y-%m-%d").date()
                        )
                    else:
                        processed_params.append(datetime.fromisoformat(value).date())
                else:
                    processed_params.append(value)

            elif param_type in (
                "timestamp",
                "datetime",
                "datetime.datetime",
                "timestamptz",
            ):
                # Convert to datetime
                if isinstance(value, str):
                    if len(value) == 10:  # Just date
                        processed_params.append(datetime.strptime(value, "%Y-%m-%d"))
                    elif "T" in value or " " in value:
                        # ISO format or space-separated
                        processed_params.append(
                            datetime.fromisoformat(value.replace("Z", "+00:00"))
                        )
                    else:
                        processed_params.append(
                            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                        )
                else:
                    processed_params.append(value)

            elif param_type in ("int", "integer"):
                processed_params.append(int(value))

            elif param_type in ("float", "decimal", "numeric", "real", "double"):
                processed_params.append(float(value))

            elif param_type in ("bool", "boolean"):
                if isinstance(value, str):
                    processed_params.append(
                        value.lower() in ("true", "1", "yes", "t", "y")
                    )
                else:
                    processed_params.append(bool(value))

            elif param_type == "json":
                if isinstance(value, str):
                    import json

                    processed_params.append(json.loads(value))
                else:
                    processed_params.append(value)

            elif param_type in ("string", "text", "varchar", "char"):
                # Explicitly string type
                processed_params.append(str(value))

            else:
                # Unknown type, pass as string
                processed_params.append(str(value))

        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Failed to convert parameter {i+1} (value: {value}) to type {param_type}: {str(e)}"
            )

    return processed_params


def extract_schema_from_query(query: str) -> Optional[str]:
    """Extract schema name from SQL query"""
    # Look for schema.table patterns
    # Handle CREATE TABLE [IF NOT EXISTS] schema.table
    patterns = [
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\.",
        (
            r"(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM|INSERT\s+INTO|DROP\s+TABLE|"
            r"ALTER\s+TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)\."
        ),
        r"(?:TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)\.",
    ]

    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)

    # Default to public schema if no schema specified
    return "public"


def determine_operation_type(query: str) -> str:
    """Determine the type of SQL operation"""
    query_upper = query.upper().strip()

    if query_upper.startswith("SELECT"):
        return "select"
    elif query_upper.startswith("INSERT"):
        return "insert"
    elif query_upper.startswith("UPDATE"):
        return "update"
    elif query_upper.startswith("DELETE"):
        return "delete"
    elif query_upper.startswith("CREATE"):
        return "create"
    elif query_upper.startswith("ALTER"):
        return "alter"
    elif query_upper.startswith("DROP"):
        return "drop"
    elif query_upper.startswith("TRUNCATE"):
        return "truncate"
    else:
        return "unknown"


@app.post("/api/query")
async def execute_raw_query(
    request: RawQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Execute raw SQL query with safety controls"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")

        # Validate API key
        user_info = await auth_manager.validate_api_key(x_api_key)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Check if this is a gateway request with X-User-Id header
        actual_user_id = user_info["user_id"]
        if x_user_id:
            # This is a request from the gateway on behalf of another user
            actual_user_id = x_user_id
            # Note: Gateway query request for user via proxy

        # Determine operation type and schema
        operation = determine_operation_type(request.query)
        schema = extract_schema_from_query(request.query)

        # Check if operation is read-only when required
        if request.read_only and operation not in ["select", "unknown"]:
            raise HTTPException(
                status_code=400,
                detail=f"Query is not read-only. Operation detected: {operation}",
            )

        # Check permissions
        has_permission = await permission_manager.check_permission(
            actual_user_id, request.database, schema, operation
        )

        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"No {operation} permission on schema {schema} "
                    f"in database {request.database}"
                ),
            )

        # Additional safety checks for dangerous operations
        query_upper = request.query.upper()

        # Block database-level operations
        blocked_patterns = [
            r"\bDROP\s+DATABASE\b",
            r"\bCREATE\s+DATABASE\b",
            r"\bALTER\s+DATABASE\b",
            r"\bGRANT\b",
            r"\bREVOKE\b",
            r"\bCREATE\s+USER\b",
            r"\bDROP\s+USER\b",
            r"\bALTER\s+USER\b",
            r"\bCREATE\s+ROLE\b",
            r"\bDROP\s+ROLE\b",
            r"\bALTER\s+ROLE\b",
        ]

        for pattern in blocked_patterns:
            if re.search(pattern, query_upper):
                raise HTTPException(
                    status_code=400,
                    detail=f"Query contains blocked operation: {pattern}",
                )

        # Warn for potentially dangerous operations
        dangerous_operations = ["DROP TABLE", "TRUNCATE", "DELETE FROM"]
        is_dangerous = any(op in query_upper for op in dangerous_operations)

        # Set timeout
        timeout = min(request.timeout_seconds or 30, 60)  # Max 60 seconds

        # Process parameters to convert types
        try:
            processed_params = process_query_params(request.params)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Execute query with timeout
        try:
            # Determine if query returns data
            returns_data = operation in ["select"] or "RETURNING" in query_upper

            if returns_data:
                result = await db_manager.execute_query(
                    actual_user_id,
                    request.database,
                    request.query,
                    processed_params,
                    fetch=True,
                    many=True,
                )

                # Convert result to list of dicts
                if result:
                    rows = [dict(row) for row in result]
                    columns = list(rows[0].keys()) if rows else []
                else:
                    rows = []
                    columns = []

                response_data = {
                    "rows": rows,
                    "columns": columns,
                    "row_count": len(rows),
                    "operation": operation,
                    "dangerous": is_dangerous,
                }
            else:
                # Execute non-SELECT query
                affected = await db_manager.execute_query(
                    actual_user_id,
                    request.database,
                    request.query,
                    processed_params,
                    fetch=False,
                )

                response_data = {
                    "affected_rows": affected,
                    "operation": operation,
                    "dangerous": is_dangerous,
                    "message": "Query executed successfully",
                }

            # Log the operation
            await audit_logger.log_operation(
                user_id=actual_user_id,
                api_key_id=user_info["key_id"],
                endpoint="/api/query",
                method="POST",
                database_name=request.database,
                schema_name=schema,
                operation=operation.upper(),
                request_body={
                    "query_length": len(request.query),
                    "params_count": len(request.params) if request.params else 0,
                    "read_only": request.read_only,
                },
                response_status=200,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

            response = SuccessResponse(
                data=response_data,
                metadata=MetadataResponse(
                    database=request.database,
                    schema_name=schema,
                    timestamp=datetime.utcnow().isoformat(),
                    request_id=request_id,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                ),
            )

            return response

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408, detail=f"Query execution timeout ({timeout} seconds)"
            )

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("raw_query_error", error=str(e), query=request.query[:100])

        # Log failed operation
        await audit_logger.log_operation(
            user_id=user_info.get("user_id") if "user_info" in locals() else None,
            api_key_id=user_info.get("key_id") if "user_info" in locals() else None,
            endpoint="/api/query",
            method="POST",
            database_name=request.database,
            operation="RAW_QUERY",
            response_status=500,
            error_message=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="QUERY_EXECUTION_ERROR",
                message=f"Failed to execute query: {str(e)}",
                details={
                    "query_preview": request.query[:100] + "..."
                    if len(request.query) > 100
                    else request.query
                },
            ),
            metadata=MetadataResponse(
                database=request.database,
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return JSONResponse(
            status_code=500, content=error_response.model_dump(mode="json")
        )
