from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import time
from datetime import datetime
import uuid
from lib.auth import auth_manager
from lib.permissions import permission_manager
from lib.logging import audit_logger, logger
from schemas.responses import (
    SuccessResponse,
    ErrorResponse,
    MetadataResponse,
    ErrorDetail,
)

app = FastAPI()


@app.post("/api/auth/validate")
async def validate_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Validate an API key and return user information"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        if not x_api_key:
            raise HTTPException(
                status_code=401, detail="API key is required in X-API-Key header"
            )

        # Validate the API key
        user_info = await auth_manager.validate_api_key(x_api_key)

        if not user_info:
            # Log failed attempt
            await audit_logger.log_operation(
                user_id=None,
                api_key_id=None,
                endpoint="/api/auth/validate",
                method="POST",
                response_status=401,
                error_message="Invalid API key",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

            error_response = ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_API_KEY",
                    message="The provided API key is invalid or has been revoked",
                ),
                metadata=MetadataResponse(
                    timestamp=datetime.utcnow().isoformat(),
                    request_id=request_id,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                ),
            )
            return JSONResponse(status_code=401, content=error_response.model_dump(mode="json"))

        # Get user's permissions
        permissions = await permission_manager.get_user_permissions(
            user_info["user_id"]
        )

        # Log successful validation
        await audit_logger.log_operation(
            user_id=user_info["user_id"],
            api_key_id=user_info["key_id"],
            endpoint="/api/auth/validate",
            method="POST",
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        response = SuccessResponse(
            data={
                "valid": True,
                "user": {
                    "id": user_info["user_id"],
                    "email": user_info["email"],
                    "organization": user_info["organization"],
                },
                "permissions": permissions,
            },
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("api_key_validation_error", error=str(e))

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An internal error occurred during validation",
            ),
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return JSONResponse(status_code=500, content=error_response.model_dump(mode="json"))


@app.get("/api/auth/permissions")
async def get_permissions(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Get user's permissions across all databases and schemas"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        if not x_api_key:
            raise HTTPException(
                status_code=401, detail="API key is required in X-API-Key header"
            )

        # Validate the API key
        user_info = await auth_manager.validate_api_key(x_api_key)

        if not user_info:
            error_response = ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_API_KEY",
                    message="The provided API key is invalid or has been revoked",
                ),
                metadata=MetadataResponse(
                    timestamp=datetime.utcnow().isoformat(),
                    request_id=request_id,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                ),
            )
            return JSONResponse(status_code=401, content=error_response.model_dump(mode="json"))

        # Check if this is a gateway request with X-User-Id header
        actual_user_id = user_info["user_id"]
        if x_user_id:
            # This is a request from the gateway on behalf of another user
            # We trust the gateway's user ID (since it already authenticated)
            actual_user_id = x_user_id
            # Note: Gateway request for user via proxy

        # Get user's permissions
        permissions = await permission_manager.get_user_permissions(actual_user_id)
        databases = await permission_manager.get_accessible_databases(actual_user_id)

        # Log the operation
        await audit_logger.log_operation(
            user_id=actual_user_id,
            api_key_id=user_info["key_id"],
            endpoint="/api/auth/permissions",
            method="GET",
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        response = SuccessResponse(
            data={"databases": databases, "permissions": permissions},
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("get_permissions_error", error=str(e))

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An internal error occurred while fetching permissions",
            ),
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return JSONResponse(status_code=500, content=error_response.model_dump(mode="json"))
