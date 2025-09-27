# PostgreSQL Multi-tenant CRUD API Server

## Project Overview
A Python-based REST API server deployed on Vercel that provides secure, multi-tenant access to PostgreSQL databases hosted on Azure. Designed for no-code/low-code platforms like Lovable and Claude Code, enabling dynamic database operations with granular permission control.

## Architecture

### Core Components
1. **API Layer**: FastAPI-based REST API with serverless functions on Vercel
2. **Authentication**: API key-based authentication
3. **Database Layer**: PostgreSQL on Azure with multi-tenant isolation
4. **Permission Management**: Schema-level read/write access control
5. **Master Database**: Separate PostgreSQL database for user and permission management

## Database Structure

### Master Database (Azure PostgreSQL)
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    organization VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Database assignments
CREATE TABLE database_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    connection_string_encrypted TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, database_name)
);

-- Schema permissions
CREATE TABLE schema_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255) NOT NULL,
    permission VARCHAR(20) NOT NULL CHECK (permission IN ('read_only', 'read_write')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, database_name, schema_name)
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    database_name VARCHAR(255),
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    operation VARCHAR(50),
    request_body JSONB,
    response_status INTEGER,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
```

### Tenant Databases (Azure PostgreSQL)
- Each user gets access to one or more dedicated databases
- Databases contain multiple schemas (public, custom schemas)
- Schemas start empty or contain existing user-created tables
- Full DDL and DML operations supported within permission boundaries

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/validate` | Validate API key |
| GET | `/api/auth/permissions` | Get user's permissions |

### Database Structure Operations (DDL)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/databases` | List accessible databases |
| GET | `/api/schemas` | List schemas in a database |
| POST | `/api/schemas` | Create new schema |
| DELETE | `/api/schemas/{schema}` | Drop schema |
| GET | `/api/tables` | List tables in a schema |
| POST | `/api/tables` | Create new table |
| PUT | `/api/tables/{table}` | Alter table structure |
| DELETE | `/api/tables/{table}` | Drop table |
| GET | `/api/tables/{table}/structure` | Get table structure |
| POST | `/api/indexes` | Create index |
| DELETE | `/api/indexes/{index}` | Drop index |
| POST | `/api/constraints` | Add constraint |
| DELETE | `/api/constraints/{constraint}` | Drop constraint |

### Data Operations (DML)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data/{schema}/{table}` | Query data with pagination/filtering |
| POST | `/api/data/{schema}/{table}` | Insert single or bulk records |
| PUT | `/api/data/{schema}/{table}` | Update records |
| PATCH | `/api/data/{schema}/{table}` | Partial update records |
| DELETE | `/api/data/{schema}/{table}` | Delete records |
| POST | `/api/data/upsert/{schema}/{table}` | Upsert records |

### Advanced Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query` | Execute raw SQL (with safety controls) |
| POST | `/api/transaction/begin` | Start transaction |
| POST | `/api/transaction/commit` | Commit transaction |
| POST | `/api/transaction/rollback` | Rollback transaction |
| POST | `/api/procedures/{procedure}` | Execute stored procedure |
| POST | `/api/functions/{function}` | Execute function |
| POST | `/api/export/{schema}/{table}` | Export data (CSV, JSON) |
| POST | `/api/import/{schema}/{table}` | Import data (CSV, JSON) |

### Admin Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/usage` | Get API usage statistics |
| GET | `/api/admin/logs` | View audit logs |

## Request/Response Formats

### Standard Request Headers
```http
X-API-Key: vibe_prod_xxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
X-Database-Name: user_db_001  # Optional, can be in body
```

### Create Table Request
```json
{
  "database": "user_db_001",
  "schema": "public",
  "table": "users",
  "columns": [
    {
      "name": "id",
      "type": "SERIAL",
      "constraints": ["PRIMARY KEY"]
    },
    {
      "name": "email",
      "type": "VARCHAR(255)",
      "constraints": ["UNIQUE", "NOT NULL"]
    },
    {
      "name": "created_at",
      "type": "TIMESTAMP",
      "default": "NOW()"
    }
  ],
  "indexes": [
    {
      "name": "idx_users_email",
      "columns": ["email"],
      "unique": false
    }
  ],
  "constraints": [
    {
      "type": "CHECK",
      "name": "email_valid",
      "condition": "email LIKE '%@%'"
    }
  ]
}
```

### Query Data Request
```json
{
  "database": "user_db_001",
  "schema": "public",
  "table": "users",
  "select": ["id", "email", "created_at"],
  "where": {
    "email": {"like": "%@example.com"},
    "created_at": {"gte": "2024-01-01"}
  },
  "order_by": [
    {"column": "created_at", "direction": "DESC"}
  ],
  "limit": 100,
  "offset": 0
}
```

### Raw SQL Query Request
```json
{
  "database": "user_db_001",
  "query": "SELECT * FROM public.users WHERE email = $1",
  "params": ["user@example.com"],
  "timeout_seconds": 30,
  "read_only": false
}
```

### Success Response
```json
{
  "success": true,
  "data": {
    "rows": [...],
    "affected_rows": 5,
    "columns": ["id", "email", "created_at"]
  },
  "metadata": {
    "database": "user_db_001",
    "schema": "public",
    "table": "users",
    "execution_time_ms": 45,
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_abc123"
  },
  "pagination": {
    "total": 1000,
    "limit": 100,
    "offset": 0,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "You don't have write access to schema 'protected'",
    "details": {
      "database": "user_db_001",
      "schema": "protected",
      "required_permission": "read_write",
      "user_permission": "read_only"
    }
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_xyz789"
  }
}
```

## Security Implementation

### API Key Format
```
vibe_[environment]_[random_32_chars]
Examples:
- vibe_prod_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
- vibe_dev_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4
```

### SQL Injection Prevention
```python
# Parameterized queries only
# Bad: f"SELECT * FROM {table} WHERE id = {user_id}"
# Good: Use asyncpg parameterized queries

async def safe_query(conn, schema, table, user_id):
    # Validate schema and table names against whitelist
    validate_identifier(schema)
    validate_identifier(table)
    
    # Use parameterized query
    query = f"SELECT * FROM {schema}.{table} WHERE id = $1"
    return await conn.fetch(query, user_id)
```

### Permission Checks
```python
class PermissionChecker:
    async def check_permission(
        self, 
        user_id: str, 
        database: str, 
        schema: str, 
        operation: str
    ) -> bool:
        # Check if user has access to database
        # Check if user has required permission on schema
        # Log the access attempt
        pass
```

### Query Safety Controls
- Maximum query execution time: 30 seconds
- Maximum rows returned: 10,000 per query
- Blocked SQL keywords for raw queries: DROP DATABASE, CREATE DATABASE
- Query complexity limits
- Resource usage monitoring

## Vercel Deployment Configuration

### Project Structure
```
vibe-coding-backend/
├── api/                    # Vercel API routes
│   ├── auth/
│   │   └── validate.py
│   ├── data/
│   │   └── [schema]/
│   │       └── [table].py
│   ├── tables/
│   │   └── index.py
│   ├── schemas/
│   │   └── index.py
│   ├── query.py
│   └── transaction/
│       ├── begin.py
│       ├── commit.py
│       └── rollback.py
├── lib/                    # Shared libraries
│   ├── auth.py
│   ├── database.py
│   ├── permissions.py
│   ├── validators.py
│   └── utils.py
├── schemas/               # Pydantic models
│   ├── requests.py
│   └── responses.py
├── middleware/
│   └── cors.py
├── vercel.json
├── requirements.txt
└── .env.local
```

### vercel.json
```json
{
  "functions": {
    "api/**/*.py": {
      "maxDuration": 60
    }
  },
  "env": {
    "MASTER_DB_URL": "@master_db_url",
    "AZURE_DB_HOST": "@azure_db_host",
    "ENCRYPTION_KEY": "@encryption_key"
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Access-Control-Allow-Methods", "value": "GET,POST,PUT,DELETE,OPTIONS" },
        { "key": "Access-Control-Allow-Headers", "value": "X-API-Key,Content-Type,X-Database-Name" }
      ]
    }
  ]
}
```

### Environment Variables
```env
# Master Database (Azure PostgreSQL)
MASTER_DB_URL=postgresql://user:pass@host.database.azure.com/master_db?sslmode=require

# Azure Database Configuration
AZURE_DB_HOST=your-server.database.azure.com
AZURE_DB_PORT=5432
AZURE_DB_SSL=require

# Security
ENCRYPTION_KEY=your-256-bit-encryption-key
API_KEY_SALT=your-salt-for-hashing

# Configuration
MAX_QUERY_TIME_SECONDS=30
MAX_ROWS_PER_QUERY=10000
DEFAULT_PAGE_SIZE=100
MAX_REQUEST_SIZE_MB=10

# Monitoring
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGS=true
SENTRY_DSN=your-sentry-dsn  # Optional
```

## Implementation Guidelines

### Database Connection Management
```python
# Use connection pooling with asyncpg
import asyncpg
from functools import lru_cache

class DatabaseManager:
    def __init__(self):
        self.pools = {}
    
    async def get_pool(self, database_url: str) -> asyncpg.Pool:
        if database_url not in self.pools:
            # Create pool with Vercel-optimized settings
            self.pools[database_url] = await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=5,  # Limited for serverless
                max_queries=50000,
                max_inactive_connection_lifetime=30,
                timeout=10,
                command_timeout=30,
                ssl='require'
            )
        return self.pools[database_url]
    
    async def execute_with_permission_check(
        self,
        user_id: str,
        database: str,
        schema: str,
        query: str,
        params: list,
        operation_type: str
    ):
        # Check permissions
        # Get connection from pool
        # Execute query
        # Log operation
        # Return results
        pass
```

### Vercel Function Example
```python
# api/data/[schema]/[table].py
from http.server import BaseHTTPRequestHandler
import json
import asyncio
from lib.auth import verify_api_key
from lib.database import DatabaseManager
from lib.permissions import check_permission

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse path parameters
        path_parts = self.path.split('/')
        schema = path_parts[-2]
        table = path_parts[-1].split('?')[0]
        
        # Verify API key
        api_key = self.headers.get('X-API-Key')
        user = verify_api_key(api_key)
        
        if not user:
            self.send_error(401, 'Invalid API key')
            return
        
        # Check permissions
        if not check_permission(user['id'], schema, 'read'):
            self.send_error(403, 'Permission denied')
            return
        
        # Execute query
        result = asyncio.run(self.query_data(user, schema, table))
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    async def query_data(self, user, schema, table):
        # Implementation here
        pass
```

## OpenAPI/Swagger Documentation

### Swagger UI Configuration
- Endpoint: `/api/docs`
- OpenAPI spec: `/api/openapi.json`
- Authentication: API key in header
- Try-it-out functionality enabled

### Auto-generated Documentation
```python
# Use FastAPI's automatic OpenAPI generation
from fastapi import FastAPI, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Vibe Coding Backend API",
    description="Multi-tenant PostgreSQL CRUD API for no-code platforms",
    version="1.0.0",
    servers=[
        {"url": "https://your-app.vercel.app", "description": "Production"},
        {"url": "http://localhost:3000", "description": "Development"}
    ]
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Vibe Coding Backend API",
        version="1.0.0",
        description="Complete CRUD operations on PostgreSQL with multi-tenant isolation",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "APIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Monitoring and Logging

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

async def log_operation(
    user_id: str,
    operation: str,
    database: str,
    schema: str,
    table: str,
    details: dict
):
    await logger.ainfo(
        "database_operation",
        user_id=user_id,
        operation=operation,
        database=database,
        schema=schema,
        table=table,
        **details
    )
```

### Metrics to Track
- API response times by endpoint
- Database query execution times
- Error rates and types
- User activity patterns
- Schema/table creation frequency
- Data volume processed

## Testing Strategy

### Unit Tests
```python
# tests/test_permissions.py
import pytest
from lib.permissions import PermissionChecker

@pytest.mark.asyncio
async def test_read_permission():
    checker = PermissionChecker()
    result = await checker.check_permission(
        user_id="test_user",
        database="test_db",
        schema="public",
        operation="read"
    )
    assert result == True
```

### Integration Tests
```python
# tests/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_table():
    async with AsyncClient(base_url="http://localhost:3000") as client:
        response = await client.post(
            "/api/tables",
            json={
                "database": "test_db",
                "schema": "public",
                "table": "test_table",
                "columns": [...]
            },
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 201
```

## Client SDK Examples

### Python Client
```python
from vibe_coding_client import VibeClient

# Initialize client
client = VibeClient(api_key="vibe_prod_xxxxx")

# Create table
client.create_table(
    database="my_db",
    schema="public",
    table="users",
    columns=[
        {"name": "id", "type": "SERIAL", "constraints": ["PRIMARY KEY"]},
        {"name": "email", "type": "VARCHAR(255)", "constraints": ["UNIQUE"]}
    ]
)

# Insert data
client.insert(
    database="my_db",
    schema="public",
    table="users",
    data=[{"email": "user@example.com"}]
)

# Query data
results = client.query(
    database="my_db",
    schema="public",
    table="users",
    where={"email": {"like": "%@example.com"}},
    limit=10
)
```

### JavaScript/TypeScript Client
```typescript
import { VibeClient } from 'vibe-coding-client';

const client = new VibeClient({
  apiKey: 'vibe_prod_xxxxx',
  baseUrl: 'https://api.your-domain.com'
});

// Create table
await client.createTable({
  database: 'my_db',
  schema: 'public',
  table: 'users',
  columns: [
    { name: 'id', type: 'SERIAL', constraints: ['PRIMARY KEY'] },
    { name: 'email', type: 'VARCHAR(255)', constraints: ['UNIQUE'] }
  ]
});

// Query with transaction
const transaction = await client.beginTransaction('my_db');
try {
  await transaction.insert('public', 'users', { email: 'user@example.com' });
  await transaction.update('public', 'users', { active: true }, { id: 1 });
  await transaction.commit();
} catch (error) {
  await transaction.rollback();
  throw error;
}
```

## Performance Optimization

### Vercel Serverless Optimizations
1. **Connection Pooling**: Reuse database connections across invocations
2. **Query Caching**: Cache frequently accessed data in memory
3. **Lazy Loading**: Load dependencies only when needed
4. **Response Streaming**: Stream large result sets
5. **Edge Caching**: Use Vercel Edge Network for static responses

### Database Optimizations
1. **Index Strategy**: Auto-suggest indexes based on query patterns
2. **Query Analysis**: EXPLAIN ANALYZE for slow queries
3. **Batch Operations**: Support bulk inserts/updates
4. **Prepared Statements**: Cache and reuse query plans

## Error Handling

### Error Codes
```python
class ErrorCodes:
    # Authentication errors (401)
    INVALID_API_KEY = "INVALID_API_KEY"
    EXPIRED_API_KEY = "EXPIRED_API_KEY"
    
    # Permission errors (403)
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SCHEMA_ACCESS_DENIED = "SCHEMA_ACCESS_DENIED"
    
    # Validation errors (400)
    INVALID_SCHEMA_NAME = "INVALID_SCHEMA_NAME"
    INVALID_TABLE_NAME = "INVALID_TABLE_NAME"
    INVALID_SQL_SYNTAX = "INVALID_SQL_SYNTAX"
    
    # Resource errors (404)
    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    SCHEMA_NOT_FOUND = "SCHEMA_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    
    # Server errors (500)
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    QUERY_TIMEOUT = "QUERY_TIMEOUT"
```

## Roadmap

### Phase 1: MVP (Weeks 1-2)
- [ ] Basic authentication with API keys
- [ ] Simple CRUD operations
- [ ] Schema/table management
- [ ] Permission system
- [ ] Swagger documentation

### Phase 2: Advanced Features (Weeks 3-4)
- [ ] Transaction support
- [ ] Stored procedures/functions
- [ ] Raw SQL execution with safety
- [ ] Bulk operations
- [ ] Export/Import functionality

### Phase 3: Production Ready (Weeks 5-6)
- [ ] Comprehensive logging
- [ ] Performance monitoring
- [ ] Rate limiting
- [ ] Client SDKs
- [ ] Advanced error handling

### Phase 4: Enterprise Features (Future)
- [ ] Query optimization advisor
- [ ] Automatic backup/restore
- [ ] Schema versioning
- [ ] Team collaboration features
- [ ] Usage analytics dashboard

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with Vercel CLI
vercel dev

# Run tests
pytest tests/ -v

# Check code quality
black .
flake8 .
mypy .

# Deploy to Vercel
vercel --prod

# View logs
vercel logs --prod
```

## Support and Documentation

- **API Documentation**: `/api/docs`
- **OpenAPI Spec**: `/api/openapi.json`
- **Status Page**: `/api/health`
- **Support Email**: support@your-domain.com

---

This backend will provide a robust, secure, and scalable API for no-code/low-code platforms to interact with PostgreSQL databases with full CRUD capabilities and fine-grained access control.