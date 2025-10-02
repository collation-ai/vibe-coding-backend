#!/usr/bin/env python3
"""
Standalone test server that runs the actual API code locally
WITHOUT needing database connections
"""

import os
import sys
import json
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
import time
from datetime import datetime
import uuid
import uvicorn

# Set mock environment variables
os.environ["ENCRYPTION_KEY"] = "TEST_KEY_FOR_LOCAL_ONLY_aaaaaaaaaaaaaaaaaaaaaaa="
os.environ["API_KEY_SALT"] = "test_salt_for_local"
os.environ["MASTER_DB_URL"] = "postgresql://mock:mock@localhost/mock"
os.environ["AZURE_DB_HOST"] = "localhost"

print("Starting standalone test server...")
print("This server uses MOCK data - no database needed")
print("-" * 60)

app = FastAPI()

# Mock data
MOCK_USERS = {
    "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ": {
        "user_id": "81c979aa-b43e-4d4a-a7eb-4bba01dc8a07",
        "email": "tanmais@collationdemo.com",
        "organization": "Collation AI",
        "key_id": "key_001"
    }
}

MOCK_PERMISSIONS = {
    "81c979aa-b43e-4d4a-a7eb-4bba01dc8a07": {
        "databases": ["master_db"],
        "permissions": [
            {"database": "master_db", "schema": "public", "permission": "read_write"},
            {"database": "master_db", "schema": "auth", "permission": "read_write"},
            {"database": "master_db", "schema": "logs", "permission": "read_only"}
        ]
    },
    "d4a34dc6-6699-4183-b068-6c7832291e4b": {
        "databases": ["cdb_written_976_poetry"],
        "permissions": [
            {"database": "cdb_written_976_poetry", "schema": "public", "permission": "read_write"}
        ]
    }
}

@app.get("/api/auth/permissions")
async def get_permissions(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Test the exact code from api/auth/validate.py"""
    print(f"\n=== /api/auth/permissions called ===")
    print(f"X-API-Key: {x_api_key[:20]}..." if x_api_key else "X-API-Key: None")
    print(f"X-User-Id: {x_user_id}")
    
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Import the actual schemas we use
        from schemas.responses import (
            SuccessResponse,
            ErrorResponse,
            MetadataResponse,
            ErrorDetail,
        )
        
        if not x_api_key:
            raise HTTPException(
                status_code=401, detail="API key is required in X-API-Key header"
            )
        
        # Mock validate API key
        user_info = MOCK_USERS.get(x_api_key)
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
            print(f"Returning 401 - Invalid API key")
            return JSONResponse(status_code=401, content=error_response.model_dump(mode="json"))
        
        # Check if this is a gateway request with X-User-Id header
        actual_user_id = user_info["user_id"]
        if x_user_id:
            # This is a request from the gateway on behalf of another user
            actual_user_id = x_user_id
            print(f"Using X-User-Id: {actual_user_id}")
        else:
            print(f"Using API key owner: {actual_user_id}")
        
        # Get mock permissions
        user_perms = MOCK_PERMISSIONS.get(actual_user_id, {
            "databases": [],
            "permissions": []
        })
        
        response = SuccessResponse(
            data={
                "databases": user_perms["databases"], 
                "permissions": user_perms["permissions"]
            },
            metadata=MetadataResponse(
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
            ),
        )
        
        print(f"Returning 200 - {len(user_perms['permissions'])} permissions")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
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

@app.post("/api/query")
async def execute_query(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Test the query endpoint"""
    print(f"\n=== /api/query called ===")
    
    body = await request.json()
    print(f"Database: {body.get('database')}")
    print(f"Query: {body.get('query')[:50]}...")
    
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    from schemas.responses import (
        SuccessResponse,
        ErrorResponse,
        MetadataResponse,
        ErrorDetail,
    )
    
    # Mock response
    response = SuccessResponse(
        data={
            "rows": [{"count": 4}],
            "columns": ["count"],
            "row_count": 1,
            "operation": "select",
            "dangerous": False
        },
        metadata=MetadataResponse(
            database=body.get("database"),
            schema_name="public",
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            execution_time_ms=int((time.time() - start_time) * 1000),
        ),
    )
    
    print("Returning mock query result")
    return response

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SERVER READY ON http://localhost:8000")
    print("="*60)
    print("\nTest with:")
    print("  curl http://localhost:8000/api/auth/permissions \\")
    print('    -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"')
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)