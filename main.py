#!/usr/bin/env python3
"""
Main FastAPI application for Vibe Coding Backend
Comprehensive API with all endpoints
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Header, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from typing import Optional, Annotated
import time
from datetime import datetime
import uuid

# Import all endpoint modules
from api.health import health_check
from api.auth.validate import validate_api_key, get_permissions
from api.tables.index import (
    create_table, list_tables, get_table_structure, drop_table
)
from api.data import (
    query_data, insert_data, update_data, delete_data
)
from api.query import execute_raw_query

# Import request/response schemas
from schemas.requests import (
    CreateTableRequest, DropTableRequest,
    InsertDataRequest, UpdateDataRequest, DeleteDataRequest,
    RawQueryRequest
)
from schemas.responses import SuccessResponse, ErrorResponse

# Create FastAPI app
app = FastAPI(
    title="Vibe Coding Backend API",
    description="Multi-tenant PostgreSQL CRUD API for no-code/low-code platforms",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security scheme for API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Health check
@app.get("/api/health", tags=["System"])
async def health_endpoint():
    """Health check endpoint"""
    return await health_check()

# Authentication endpoints
@app.post("/api/auth/validate", tags=["Authentication"])
async def validate_api_key_endpoint(
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Validate API key and return user information"""
    return await validate_api_key(x_api_key)

@app.get("/api/auth/permissions", tags=["Authentication"])
async def get_permissions_endpoint(
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Get user's permissions across databases and schemas"""
    return await get_permissions(x_api_key)

# Database structure operations (DDL)
@app.post("/api/tables", tags=["Tables"], status_code=201)
async def create_table_endpoint(
    request: CreateTableRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Create a new table in the database
    
    Creates a new table with specified columns, constraints, and indexes.
    Requires 'write' permission on the target schema.
    """
    return await create_table(request, x_api_key)

@app.get("/api/tables", tags=["Tables"])
async def list_tables_endpoint(
    database: str,
    schema: str = "public",
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """List all tables in a schema
    
    Returns a list of all tables in the specified database schema.
    Requires at least 'read' permission on the schema.
    """
    return await list_tables(database, schema, x_api_key)

@app.get("/api/tables/{table}/structure", tags=["Tables"])
async def get_table_structure_endpoint(
    table: str,
    database: str,
    schema: str = "public",
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Get the structure of a table
    
    Returns detailed information about table columns, types, and constraints.
    Requires at least 'read' permission on the schema.
    """
    return await get_table_structure(table, database, schema, x_api_key)

@app.delete("/api/tables/{table}", tags=["Tables"])
async def drop_table_endpoint(
    table: str,
    request: DropTableRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Drop a table from the database
    
    Permanently deletes a table and all its data.
    Use 'cascade' option to drop dependent objects.
    Requires 'write' permission on the schema.
    """
    return await drop_table(table, request, x_api_key)

# Data operations (DML)
@app.get("/api/data/{schema}/{table}", tags=["Data"])
async def query_data_endpoint(
    schema: str,
    table: str,
    database: str,
    select: str = None,
    where: str = None,
    order_by: str = None,
    order: str = "ASC",
    limit: int = 100,
    offset: int = 0,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Query data from a table with filtering and pagination
    
    Retrieve rows from a table with optional filtering, sorting, and pagination.
    - select: Comma-separated column names (default: all columns)
    - where: JSON string with filter conditions
    - order_by: Column to sort by
    - order: Sort direction (ASC or DESC)
    - limit: Maximum rows to return
    - offset: Number of rows to skip
    """
    return await query_data(
        schema, table, database, select, where, 
        order_by, order, limit, offset, x_api_key
    )

@app.post("/api/data/{schema}/{table}", tags=["Data"], status_code=201)
async def insert_data_endpoint(
    schema: str,
    table: str,
    request: InsertDataRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Insert data into a table
    
    Insert single or multiple records into the specified table.
    Supports bulk inserts and returning specific columns.
    Requires 'write' permission on the schema.
    """
    return await insert_data(schema, table, request, x_api_key)

@app.put("/api/data/{schema}/{table}", tags=["Data"])
async def update_data_endpoint(
    schema: str,
    table: str,
    request: UpdateDataRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Update data in a table
    
    Update existing records based on WHERE conditions.
    Requires 'write' permission on the schema.
    """
    return await update_data(schema, table, request, x_api_key)

@app.delete("/api/data/{schema}/{table}", tags=["Data"])
async def delete_data_endpoint(
    schema: str,
    table: str,
    request: DeleteDataRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Delete data from a table
    
    Delete records based on WHERE conditions.
    Requires 'write' permission on the schema.
    """
    return await delete_data(schema, table, request, x_api_key)

# Raw SQL query
@app.post("/api/query", tags=["Query"])
async def execute_query_endpoint(
    request: RawQueryRequest,
    x_api_key: Annotated[Optional[str], Security(api_key_header)] = None
):
    """Execute raw SQL query with safety controls
    
    Execute custom SQL queries with parameterized inputs for safety.
    Read-only queries require 'read' permission.
    Modifying queries require 'write' permission.
    """
    return await execute_raw_query(request, x_api_key)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Vibe Coding Backend API",
        version="1.0.0",
        description="""
        ## Multi-tenant PostgreSQL CRUD API
        
        This API provides secure, multi-tenant access to PostgreSQL databases for no-code/low-code platforms.
        
        ### Features
        - 🔐 API key authentication
        - 🏢 Multi-tenant database isolation
        - 🔒 Schema-level permissions (read-only/read-write)
        - 📊 Full CRUD operations
        - 🏗️ Dynamic table creation (DDL)
        - 🔄 Transaction support
        - 📝 Raw SQL execution with safety controls
        
        ### Authentication
        All endpoints (except /api/health) require an API key in the `X-API-Key` header.
        
        ### Getting Started
        1. Create a user using the admin script
        2. Generate an API key
        3. Assign a database to the user
        4. Grant permissions on schemas
        5. Start making API calls
        
        ### Permission Levels
        - **read_only**: SELECT operations only
        - **read_write**: All operations (SELECT, INSERT, UPDATE, DELETE, CREATE, etc.)
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        }
    }
    
    # Add security to all endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if path != "/api/health":
                openapi_schema["paths"][path][method]["security"] = [
                    {"APIKeyHeader": []}
                ]
    
    # Update example values for better documentation
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        # Update CreateTableRequest examples
        if "CreateTableRequest" in openapi_schema["components"]["schemas"]:
            openapi_schema["components"]["schemas"]["CreateTableRequest"]["example"] = {
                "database": "user_db_001",
                "schema": "public",
                "table": "users",
                "columns": [
                    {"name": "id", "type": "SERIAL", "constraints": ["PRIMARY KEY"]},
                    {"name": "email", "type": "VARCHAR(255)", "constraints": ["UNIQUE", "NOT NULL"]},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "created_at", "type": "TIMESTAMP", "default": "NOW()"}
                ],
                "if_not_exists": True
            }
        
        # Update InsertDataRequest examples
        if "InsertDataRequest" in openapi_schema["components"]["schemas"]:
            openapi_schema["components"]["schemas"]["InsertDataRequest"]["example"] = {
                "database": "user_db_001",
                "data": {"email": "john@example.com", "name": "John Doe"},
                "returning": ["id", "created_at"]
            }
        
        # Update RawQueryRequest examples
        if "RawQueryRequest" in openapi_schema["components"]["schemas"]:
            openapi_schema["components"]["schemas"]["RawQueryRequest"]["example"] = {
                "database": "user_db_001",
                "query": "SELECT * FROM public.users WHERE created_at > $1 AND active = $2 LIMIT $3",
                "params": [
                    {"value": "2024-01-01", "type": "date"},
                    {"value": "true", "type": "boolean"},
                    {"value": "10", "type": "integer"}
                ],
                "read_only": True
            }
        
        # Add more detailed examples for QueryParameter
        if "QueryParameter" in openapi_schema["components"]["schemas"]:
            openapi_schema["components"]["schemas"]["QueryParameter"]["examples"] = {
                "date_param": {
                    "summary": "Date parameter",
                    "value": {"value": "2024-01-01", "type": "date"}
                },
                "timestamp_param": {
                    "summary": "Timestamp parameter",
                    "value": {"value": "2024-01-01 14:30:00", "type": "timestamp"}
                },
                "integer_param": {
                    "summary": "Integer parameter",
                    "value": {"value": "42", "type": "integer"}
                },
                "float_param": {
                    "summary": "Float parameter",
                    "value": {"value": "99.99", "type": "float"}
                },
                "boolean_param": {
                    "summary": "Boolean parameter",
                    "value": {"value": "true", "type": "boolean"}
                },
                "string_param": {
                    "summary": "String parameter",
                    "value": {"value": "example text", "type": "string"}
                },
                "json_param": {
                    "summary": "JSON parameter",
                    "value": {"value": "{\"key\": \"value\"}", "type": "json"}
                }
            }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Vibe Coding Backend API")
    print("-" * 50)
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("OpenAPI: http://localhost:8000/openapi.json")
    print("-" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )