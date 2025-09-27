from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class ColumnDefinition(BaseModel):
    name: str = Field(..., min_length=1, max_length=63)
    type: str = Field(..., min_length=1, max_length=100)
    constraints: Optional[List[str]] = []
    default: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{0,62}$', v):
            raise ValueError('Invalid column name')
        return v


class IndexDefinition(BaseModel):
    name: str = Field(..., min_length=1, max_length=63)
    columns: List[str] = Field(..., min_items=1)
    unique: bool = False
    method: Optional[str] = "btree"  # btree, hash, gin, gist


class ConstraintDefinition(BaseModel):
    type: str = Field(...)  # CHECK, FOREIGN KEY, UNIQUE
    name: str = Field(..., min_length=1, max_length=63)
    condition: Optional[str] = None  # For CHECK constraints
    columns: Optional[List[str]] = None  # For UNIQUE constraints
    references: Optional[str] = None  # For FOREIGN KEY


class CreateTableRequest(BaseModel):
    database: str
    schema_name: str = Field(default="public", alias="schema")
    table: str = Field(..., min_length=1, max_length=63)
    columns: List[ColumnDefinition]
    indexes: Optional[List[IndexDefinition]] = []
    constraints: Optional[List[ConstraintDefinition]] = []
    if_not_exists: bool = True


class AlterTableRequest(BaseModel):
    database: str
    schema_name: str = Field(default="public", alias="schema")
    table: str
    action: str  # ADD_COLUMN, DROP_COLUMN, RENAME_COLUMN, ALTER_COLUMN
    column: Optional[ColumnDefinition] = None
    old_column_name: Optional[str] = None
    new_column_name: Optional[str] = None


class DropTableRequest(BaseModel):
    database: str
    schema_name: str = Field(default="public", alias="schema")
    table: str
    cascade: bool = False
    if_exists: bool = True


class WhereCondition(BaseModel):
    column: str
    operator: str = "="  # =, !=, >, <, >=, <=, LIKE, IN, IS NULL, IS NOT NULL
    value: Any
    
    @validator('operator')
    def validate_operator(cls, v):
        allowed = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE', 'IN', 'NOT IN', 'IS NULL', 'IS NOT NULL']
        if v.upper() not in allowed:
            raise ValueError(f'Invalid operator. Must be one of: {allowed}')
        return v.upper()


class OrderBy(BaseModel):
    column: str
    direction: str = "ASC"
    
    @validator('direction')
    def validate_direction(cls, v):
        if v.upper() not in ['ASC', 'DESC']:
            raise ValueError('Direction must be ASC or DESC')
        return v.upper()


class QueryDataRequest(BaseModel):
    database: str
    schema_name: str = Field(default="public", alias="schema")
    table: str
    select: Optional[List[str]] = None  # None means SELECT *
    where: Optional[Union[Dict[str, Any], List[WhereCondition]]] = None
    order_by: Optional[List[OrderBy]] = None
    limit: Optional[int] = Field(None, le=10000)
    offset: Optional[int] = Field(0, ge=0)
    distinct: bool = False


class InsertDataRequest(BaseModel):
    database: str
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    returning: Optional[List[str]] = None
    on_conflict: Optional[str] = None  # Column name for ON CONFLICT
    on_conflict_action: Optional[str] = "DO NOTHING"  # DO NOTHING or DO UPDATE


class UpdateDataRequest(BaseModel):
    database: str
    set: Dict[str, Any]
    where: Optional[Union[Dict[str, Any], List[WhereCondition]]] = None
    returning: Optional[List[str]] = None


class DeleteDataRequest(BaseModel):
    database: str
    where: Union[Dict[str, Any], List[WhereCondition]]
    returning: Optional[List[str]] = None


class QueryParameter(BaseModel):
    value: Any = Field(..., description="The parameter value")
    type: str = Field(..., description="Data type: string, integer, float, boolean, date, timestamp, json")
    
    class Config:
        extra = 'forbid'
        schema_extra = {
            "example": {
                "value": "2024-01-01",
                "type": "date"
            }
        }


class RawQueryRequest(BaseModel):
    database: str = Field(..., description="Target database name", example="user_db_001")
    query: str = Field(
        ..., 
        max_length=50000, 
        description="SQL query with $1, $2, etc. for parameters",
        example="SELECT * FROM users WHERE created_at > $1 AND status = $2 LIMIT $3"
    )
    params: List[QueryParameter] = Field(
        default=[], 
        description="Query parameters with required type information",
        example=[
            {"value": "2024-01-01", "type": "date"},
            {"value": "active", "type": "string"},
            {"value": "10", "type": "integer"}
        ]
    )
    timeout_seconds: Optional[int] = Field(30, le=60, ge=1, description="Query timeout in seconds")
    read_only: bool = Field(False, description="If true, only SELECT queries are allowed")
    
    class Config:
        schema_extra = {
            "example": {
                "database": "minerva_pear",
                "query": "SELECT COUNT(*) FROM users WHERE created_at BETWEEN $1 AND $2",
                "params": [
                    {"value": "2024-01-01", "type": "timestamp"},
                    {"value": "2024-12-31 23:59:59", "type": "timestamp"}
                ],
                "read_only": True
            }
        }
    
    @validator('query')
    def validate_query(cls, v):
        # Block dangerous operations
        blocked_keywords = [
            'DROP DATABASE', 'CREATE DATABASE', 'ALTER DATABASE',
            'GRANT', 'REVOKE', 'CREATE USER', 'DROP USER', 'ALTER USER',
            'CREATE ROLE', 'DROP ROLE', 'ALTER ROLE'
        ]
        query_upper = v.upper()
        for keyword in blocked_keywords:
            if keyword in query_upper:
                raise ValueError(f'Query contains blocked operation: {keyword}')
        return v


class TransactionRequest(BaseModel):
    database: str
    transaction_id: Optional[str] = None  # For COMMIT/ROLLBACK


class CreateSchemaRequest(BaseModel):
    database: str
    schema_name: str = Field(..., min_length=1, max_length=63, alias="schema")
    if_not_exists: bool = True


class ExportRequest(BaseModel):
    database: str
    schema_name: str = Field(default="public", alias="schema")
    table: str
    format: str = "json"  # json, csv
    where: Optional[Union[Dict[str, Any], List[WhereCondition]]] = None
    columns: Optional[List[str]] = None