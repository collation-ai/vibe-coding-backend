from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class MetadataResponse(BaseModel):
    database: Optional[str] = None
    schema_name: Optional[str] = Field(None, alias="schema")
    table: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime
    request_id: str

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class PaginationResponse(BaseModel):
    total: Optional[int] = None
    limit: int
    offset: int
    has_next: bool = False
    has_prev: bool = False


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    metadata: MetadataResponse
    pagination: Optional[PaginationResponse] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    metadata: MetadataResponse


class TableStructure(BaseModel):
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    is_primary_key: bool = False
    is_unique: bool = False
    foreign_key: Optional[Dict[str, str]] = None


class SchemaInfo(BaseModel):
    schema_name: str
    owner: str
    tables_count: int
    permission: str


class DatabaseInfo(BaseModel):
    database_name: str
    size: Optional[str] = None
    schemas: List[str]
    accessible: bool


class PermissionInfo(BaseModel):
    database: str
    schema_name: str = Field(..., alias="schema")
    permission: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApiKeyInfo(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool


class TransactionResponse(BaseModel):
    transaction_id: str
    status: str  # STARTED, COMMITTED, ROLLED_BACK
    started_at: datetime
    database: str


class QueryResultResponse(BaseModel):
    rows: List[Dict[str, Any]]
    columns: List[str]
    affected_rows: Optional[int] = None
    row_count: int


class BulkOperationResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    errors: Optional[List[Dict[str, str]]] = None


class ExportResponse(BaseModel):
    format: str
    row_count: int
    data: Union[List[Dict[str, Any]], str]  # JSON list or CSV string
    columns: List[str]


class HealthCheckResponse(BaseModel):
    status: str = "healthy"
    version: str
    database: bool
    timestamp: datetime
