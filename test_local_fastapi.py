#!/usr/bin/env python3
"""
Local FastAPI test server to debug the permissions endpoint
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import time
from datetime import datetime
import uuid
import asyncio
import uvicorn

# Import our modules
from lib.auth import auth_manager
from lib.permissions import permission_manager
from lib.logging import audit_logger
from schemas.responses import (
    SuccessResponse,
    ErrorResponse,
    MetadataResponse,
    ErrorDetail,
)

app = FastAPI()


@app.get("/test/permissions")
async def test_permissions(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Test version of the permissions endpoint"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    print(f"=== TEST ENDPOINT CALLED ===")
    print(f"X-API-Key: {x_api_key}")
    print(f"X-User-Id: {x_user_id}")
    print(f"X-User-Id type: {type(x_user_id)}")

    try:
        if not x_api_key:
            raise HTTPException(
                status_code=401, detail="API key is required in X-API-Key header"
            )

        # Validate the API key
        print("Validating API key...")
        user_info = await auth_manager.validate_api_key(x_api_key)
        print(f"User info: {user_info}")

        if not user_info:
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})

        # Check if this is a gateway request with X-User-Id header
        actual_user_id = user_info["user_id"]
        print(f"Default user_id from API key: {actual_user_id}")

        if x_user_id:
            print(f"X-User-Id provided: {x_user_id}")
            actual_user_id = x_user_id
            print(f"Using X-User-Id: {actual_user_id}")

        # Get user's permissions
        print(f"Getting permissions for user_id: {actual_user_id}")
        permissions = await permission_manager.get_user_permissions(actual_user_id)
        print(f"Permissions result: {permissions}")

        print(f"Getting databases for user_id: {actual_user_id}")
        databases = await permission_manager.get_accessible_databases(actual_user_id)
        print(f"Databases result: {databases}")

        # Log the operation
        await audit_logger.log_operation(
            user_id=actual_user_id,
            api_key_id=user_info["key_id"],
            endpoint="/test/permissions",
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

        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message=f"An unexpected error occurred: {str(e)}",
            ),
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )

        return JSONResponse(
            status_code=500, content=error_response.model_dump(mode="json")
        )


if __name__ == "__main__":
    print("Starting local test server on http://localhost:8888")
    print("Test endpoint: http://localhost:8888/test/permissions")
    uvicorn.run(app, host="0.0.0.0", port=8888)
