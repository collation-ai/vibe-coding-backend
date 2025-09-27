from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
import time
from datetime import datetime
import uuid
from lib.auth import auth_manager
from lib.permissions import permission_manager
from lib.database import db_manager
from lib.logging import audit_logger, logger
from schemas.requests import CreateTableRequest, AlterTableRequest, DropTableRequest
from schemas.responses import SuccessResponse, ErrorResponse, MetadataResponse, ErrorDetail, TableStructure

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


@app.post("/api/tables")
async def create_table(
    request: CreateTableRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Create a new table in the database"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        schema_name = request.schema_name
        user_info = await verify_auth_and_permission(
            x_api_key,
            request.database,
            schema_name,
            "create"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema_name):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(request.table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Build CREATE TABLE SQL
        columns_sql = []
        for col in request.columns:
            col_def = f"{col.name} {col.type}"
            if col.default:
                col_def += f" DEFAULT {col.default}"
            if col.constraints:
                col_def += " " + " ".join(col.constraints)
            columns_sql.append(col_def)
        
        # Add constraints if any
        for constraint in request.constraints or []:
            if constraint.type == "CHECK":
                columns_sql.append(f"CONSTRAINT {constraint.name} CHECK ({constraint.condition})")
            elif constraint.type == "UNIQUE" and constraint.columns:
                columns_sql.append(f"CONSTRAINT {constraint.name} UNIQUE ({', '.join(constraint.columns)})")
            elif constraint.type == "FOREIGN KEY" and constraint.columns and constraint.references:
                columns_sql.append(
                    f"CONSTRAINT {constraint.name} FOREIGN KEY ({', '.join(constraint.columns)}) "
                    f"REFERENCES {constraint.references}"
                )
        
        if_not_exists = "IF NOT EXISTS" if request.if_not_exists else ""
        create_sql = f"""
            CREATE TABLE {if_not_exists} {schema_name}.{request.table} (
                {', '.join(columns_sql)}
            )
        """
        
        # Execute the CREATE TABLE statement
        await db_manager.execute_query(
            user_info['user_id'],
            request.database,
            create_sql,
            fetch=False
        )
        
        # Create indexes if specified
        for index in request.indexes or []:
            unique = "UNIQUE" if index.unique else ""
            index_sql = f"""
                CREATE {unique} INDEX IF NOT EXISTS {index.name}
                ON {schema_name}.{request.table} ({', '.join(index.columns)})
                {f'USING {index.method}' if index.method != 'btree' else ''}
            """
            await db_manager.execute_query(
                user_info['user_id'],
                request.database,
                index_sql,
                fetch=False
            )
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint="/api/tables",
            method="POST",
            database_name=request.database,
            schema_name=schema_name,
            table_name=request.table,
            operation="CREATE_TABLE",
            request_body=request.model_dump(),
            response_status=201,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "message": f"Table {schema_name}.{request.table} created successfully",
                "table": request.table,
                "schema": schema_name,
                "database": request.database
            },
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema_name,
                table=request.table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=201, content=response.model_dump(mode='json'))
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("create_table_error", error=str(e))
        
        await audit_logger.log_operation(
            user_id=user_info.get('user_id') if 'user_info' in locals() else None,
            api_key_id=user_info.get('key_id') if 'user_info' in locals() else None,
            endpoint="/api/tables",
            method="POST",
            database_name=request.database,
            schema_name=schema_name,
            table_name=request.table,
            operation="CREATE_TABLE",
            request_body=request.model_dump(),
            response_status=500,
            error_message=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="CREATE_TABLE_ERROR",
                message=f"Failed to create table: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema_name,
                table=request.table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.get("/api/tables")
async def list_tables(
    database: str,
    schema: str = "public",
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List all tables in a schema"""
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
            "list"
        )
        
        # Query to list tables
        query = """
            SELECT 
                table_name,
                table_type,
                obj_description(c.oid) as comment
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            WHERE table_schema = $1
            ORDER BY table_name
        """
        
        rows = await db_manager.execute_query(
            user_info['user_id'],
            database,
            query,
            [schema]
        )
        
        tables = [
            {
                "name": row['table_name'],
                "type": row['table_type'],
                "comment": row['comment']
            }
            for row in rows
        ]
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint="/api/tables",
            method="GET",
            database_name=database,
            schema_name=schema,
            operation="LIST_TABLES",
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "tables": tables,
                "count": len(tables)
            },
            metadata=MetadataResponse(
                database=database,
                schema_name=schema,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("list_tables_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="LIST_TABLES_ERROR",
                message=f"Failed to list tables: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=database,
                schema_name=schema,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.get("/api/tables/{table}/structure")
async def get_table_structure(
    table: str,
    database: str,
    schema: str = "public",
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Get the structure of a table"""
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
            "describe"
        )
        
        # Query to get table structure
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                CASE WHEN u.column_name IS NOT NULL THEN true ELSE false END as is_unique
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.table_schema = $1 AND tc.table_name = $2
                    AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.table_schema = $1 AND tc.table_name = $2
                    AND tc.constraint_type = 'UNIQUE'
            ) u ON c.column_name = u.column_name
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position
        """
        
        rows = await db_manager.execute_query(
            user_info['user_id'],
            database,
            query,
            [schema, table]
        )
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"Table {schema}.{table} not found")
        
        columns = [
            TableStructure(
                column_name=row['column_name'],
                data_type=row['data_type'],
                is_nullable=row['is_nullable'] == 'YES',
                column_default=row['column_default'],
                character_maximum_length=row['character_maximum_length'],
                numeric_precision=row['numeric_precision'],
                numeric_scale=row['numeric_scale'],
                is_primary_key=row['is_primary_key'],
                is_unique=row['is_unique']
            ).dict()
            for row in rows
        ]
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/tables/{table}/structure",
            method="GET",
            database_name=database,
            schema_name=schema,
            table_name=table,
            operation="DESCRIBE_TABLE",
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "table": table,
                "schema": schema,
                "columns": columns
            },
            metadata=MetadataResponse(
                database=database,
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
        await logger.aerror("get_table_structure_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="DESCRIBE_TABLE_ERROR",
                message=f"Failed to get table structure: {str(e)}"
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


@app.delete("/api/tables/{table}")
async def drop_table(
    table: str,
    request: DropTableRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Drop a table from the database"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Verify auth and permissions
        schema_name = request.schema_name
        user_info = await verify_auth_and_permission(
            x_api_key,
            request.database,
            schema_name,
            "drop"
        )
        
        # Validate identifiers
        if not await db_manager.validate_identifier(schema_name):
            raise HTTPException(status_code=400, detail="Invalid schema name")
        if not await db_manager.validate_identifier(table):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        # Build DROP TABLE SQL
        if_exists = "IF EXISTS" if request.if_exists else ""
        cascade = "CASCADE" if request.cascade else ""
        drop_sql = f"DROP TABLE {if_exists} {schema_name}.{table} {cascade}"
        
        # Execute the DROP TABLE statement
        await db_manager.execute_query(
            user_info['user_id'],
            request.database,
            drop_sql,
            fetch=False
        )
        
        # Log the operation
        await audit_logger.log_operation(
            user_id=user_info['user_id'],
            api_key_id=user_info['key_id'],
            endpoint=f"/api/tables/{table}",
            method="DELETE",
            database_name=request.database,
            schema_name=schema_name,
            table_name=table,
            operation="DROP_TABLE",
            request_body=request.model_dump(),
            response_status=200,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        response = SuccessResponse(
            data={
                "message": f"Table {schema_name}.{table} dropped successfully",
                "table": table,
                "schema": schema_name,
                "database": request.database
            },
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema_name,
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
        await logger.aerror("drop_table_error", error=str(e))
        
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="DROP_TABLE_ERROR",
                message=f"Failed to drop table: {str(e)}"
            ),
            metadata=MetadataResponse(
                database=request.database,
                schema_name=schema_name,
                table=table,
                timestamp=datetime.utcnow(),
                request_id=request_id,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        )
        
        return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))