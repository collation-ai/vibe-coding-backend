from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import time
from datetime import datetime
import uuid
import json
from lib.auth import auth_manager
from lib.permissions import permission_manager
from lib.database import db_manager
from lib.logging import audit_logger, logger
from schemas.requests import QueryDataRequest, InsertDataRequest, UpdateDataRequest, DeleteDataRequest
from schemas.responses import SuccessResponse, ErrorResponse, MetadataResponse, ErrorDetail, QueryResultResponse, PaginationResponse

app = FastAPI()


async def verify_auth_and_permission(
    x_api_key: str,
    database: str,
    schema: str,
    operation: str
):
    """Verify authentication and check permissions"""
    user_info = await auth_manager.validate_api_key(x_api_key)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    has_permission = await permission_manager.check_permission(
        user_info['user_id'],
        database,
        schema,
        operation
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"No {operation} permission on schema {schema}"
        )
    
    return user_info


@app.get("/api/data/{schema}/{table}")
async def query_data(
    schema: str,
    table: str,
    database: str = Query(...),
    select: Optional[str] = Query(None, description="Comma-separated columns"),
    where: Optional[str] = Query(None, description="JSON WHERE conditions"),
    order_by: Optional[str] = Query(None, description="Column to order by"),
    order: Optional[str] = Query("ASC", description="ASC or DESC"),
    limit: Optional[int] = Query(100, le=10000),
    offset: Optional[int] = Query(0, ge=0),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Query data from a table with filtering and pagination"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        user_info = await verify_auth_and_permission(
            x_api_key,
            database,
            schema,
            "select"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Build SELECT query
        columns = select.split(',') if select else ['*']
        columns_str = ', '.join(columns) if select else '*'
        
        # Base query
        query_parts = [f"SELECT {columns_str} FROM {schema}.{table}"]
        params = []
        param_count = 0
        
        # Add WHERE clause if provided
        if where:
            try:
                where_conditions = json.loads(where)
                where_clauses = []
                for col, value in where_conditions.items():
                    param_count += 1
                    where_clauses.append(f"{col} = ${param_count}")
                    params.append(value)
                
                if where_clauses:
                    query_parts.append(f"WHERE {' AND '.join(where_clauses)}")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid WHERE conditions JSON")
        
        # Add ORDER BY clause
        if order_by:
            if not await db_manager.validate_identifier(order_by):
                raise HTTPException(status_code=400, detail="Invalid order_by column")
            query_parts.append(f"ORDER BY {order_by} {order}")
        
        # Add LIMIT and OFFSET
        query_parts.append(f"LIMIT {limit} OFFSET {offset}")
        
        # Execute query
        query_str = ' '.join(query_parts)
        rows = await db_manager.execute_query(
            user_info['user_id'],
            database,
            query_str,
            params
        )
        
        # Convert rows to list of dicts
        result_rows = [dict(row) for row in rows] if rows else []
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) as count FROM {schema}.{table}"
        if where and params:
            where_clauses = []
            for i, col in enumerate(where_conditions.keys(), 1):
                where_clauses.append(f"{col} = ${i}")
            count_query += f" WHERE {' AND '.join(where_clauses)}"
        
        count_result = await db_manager.execute_query(
            user_info['user_id'],
            database,
            count_query,
            params[:len(where_conditions)] if where else [],
            many=False
        )
        total = count_result['count'] if count_result else 0
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/data/{schema}/{table}",
            method="GET",
            database_name=database,
            schema_name=schema,
            table_name=table,
            operation="SELECT",
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "rows": result_rows,
                "row_count": len(result_rows)
            },
            metadata=MetadataResponse(
                database=database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            ),
            pagination=PaginationResponse(
                total=total,
                limit=limit,
                offset=offset,
                has_next=offset + limit < total,
                has_prev=offset > 0
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("query_data_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="QUERY_ERROR",
                message=f"Failed to query data: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.post("/api/data/{schema}/{table}")
async def insert_data(
    schema: str,
    table: str,
    request: InsertDataRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Insert data into a table"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        user_info = await verify_auth_and_permission(
            x_api_key,
            request.database,
            schema,
            "insert"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Prepare data for insertion
        is_bulk = isinstance(request.data, list)
        data_list = request.data if is_bulk else [request.data]
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Get column names from first record
        columns = list(data_list[0].keys())
        for col in columns:
            if not await db_manager.validate_identifier(col):
                raise HTTPException(status_code=400, detail=f"Invalid column name: {col}")
        
        inserted_rows = []
        
        for record in data_list:
            # Build INSERT query
            placeholders = [f"${i+1}" for i in range(len(columns))]
            returning_clause = f"RETURNING {', '.join(request.returning)}" if request.returning else "RETURNING *"
            
            insert_query = f"""
                INSERT INTO {schema}.{table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                {returning_clause}
            """
            
            # Get values in same order as columns
            values = [record.get(col) for col in columns]
            
            # Execute insert
            result = await db_manager.execute_query(
                user_info['user_id'],
                request.database,
                insert_query,
                values,
                many=False
            )
            
            if result:
                inserted_rows.append(dict(result))
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/data/{schema}/{table}",
            method="POST",
            database_name=request.database,
            schema_name=schema,
            table_name=table,
            operation="INSERT",
            request_body={"records": len(data_list)},
            response_status=201,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "message": f"Successfully inserted {len(inserted_rows)} record(s)",
                "inserted": len(inserted_rows),
                "rows": inserted_rows if request.returning else None
            },
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=201, content=response.model_dump(mode='json'))
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("insert_data_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INSERT_ERROR",
                message=f"Failed to insert data: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.put("/api/data/{schema}/{table}")
async def update_data(
    schema: str,
    table: str,
    request: UpdateDataRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Update data in a table"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        user_info = await verify_auth_and_permission(
            x_api_key,
            request.database,
            schema,
            "update"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Build UPDATE query
        set_clauses = []
        params = []
        param_count = 0
        
        # Build SET clause
        for col, value in request.set.items():
            if not await db_manager.validate_identifier(col):
                raise HTTPException(status_code=400, detail=f"Invalid column name: {col}")
            param_count += 1
            set_clauses.append(f"{col} = ${param_count}")
            params.append(value)
        
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No columns to update")
        
        # Build WHERE clause
        where_clauses = []
        if request.where:
            if isinstance(request.where, dict):
                for col, value in request.where.items():
                    param_count += 1
                    where_clauses.append(f"{col} = ${param_count}")
                    params.append(value)
        
        if not where_clauses:
            raise HTTPException(
                status_code=400, 
                detail="WHERE clause is required for UPDATE to prevent accidental updates of all rows"
            )
        
        returning_clause = f"RETURNING {', '.join(request.returning)}" if request.returning else ""
        
        update_query = f"""
            UPDATE {schema}.{table}
            SET {', '.join(set_clauses)}
            WHERE {' AND '.join(where_clauses)}
            {returning_clause}
        """
        
        # Execute update
        result = await db_manager.execute_query(
            user_info['user_id'],
            request.database,
            update_query,
            params,
            fetch=bool(request.returning)
        )
        
        if request.returning and result:
            updated_rows = [dict(row) for row in result]
        else:
            updated_rows = None
            affected_rows = result
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/data/{schema}/{table}",
            method="PUT",
            database_name=request.database,
            schema_name=schema,
            table_name=table,
            operation="UPDATE",
            request_body={"set": request.set, "where": request.where},
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "message": f"Update successful",
                "affected_rows": affected_rows if not request.returning else len(updated_rows),
                "rows": updated_rows
            },
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("update_data_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="UPDATE_ERROR",
                message=f"Failed to update data: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.delete("/api/data/{schema}/{table}")
async def delete_data(
    schema: str,
    table: str,
    request: DeleteDataRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Delete data from a table"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        user_info = await verify_auth_and_permission(
            x_api_key,
            request.database,
            schema,
            "delete"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Build DELETE query
        where_clauses = []
        params = []
        param_count = 0
        
        # Build WHERE clause
        if isinstance(request.where, dict):
            for col, value in request.where.items():
                param_count += 1
                where_clauses.append(f"{col} = ${param_count}")
                params.append(value)
        
        if not where_clauses:
            raise HTTPException(
                status_code=400,
                detail="WHERE clause is required for DELETE to prevent accidental deletion of all rows"
            )
        
        returning_clause = f"RETURNING {', '.join(request.returning)}" if request.returning else ""
        
        delete_query = f"""
            DELETE FROM {schema}.{table}
            WHERE {' AND '.join(where_clauses)}
            {returning_clause}
        """
        
        # Execute delete
        result = await db_manager.execute_query(
            user_info['user_id'],
            request.database,
            delete_query,
            params,
            fetch=bool(request.returning)
        )
        
        if request.returning and result:
            deleted_rows = [dict(row) for row in result]
        else:
            deleted_rows = None
            affected_rows = result
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/data/{schema}/{table}",
            method="DELETE",
            database_name=request.database,
            schema_name=schema,
            table_name=table,
            operation="DELETE",
            request_body={"where": request.where},
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "message": f"Delete successful",
                "affected_rows": affected_rows if not request.returning else len(deleted_rows),
                "rows": deleted_rows
            },
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("delete_data_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="DELETE_ERROR",
                message=f"Failed to delete data: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))