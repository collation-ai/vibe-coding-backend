# Vibe Coding Backend

Multi-tenant PostgreSQL CRUD API server for no-code/low-code platforms like Lovable and Claude Code.

## 🎉 Project Status: **COMPLETE & READY TO USE!**

All features are fully implemented and tested. The backend is ready for local testing and Azure deployment.

## ✨ Features

- ✅ **API Key Authentication** - Secure access with API keys in headers
- ✅ **User Management** - Admin tools for creating users and managing permissions
- ✅ **Table Operations** - Create, list, describe, and drop tables dynamically
- ✅ **Data CRUD** - Full INSERT, SELECT, UPDATE, DELETE operations
- ✅ **Raw SQL Execution** - Execute custom queries with typed parameters and safety controls
- ✅ **Type-Safe Parameters** - Automatic conversion for date, timestamp, integer, float, boolean types
- ✅ **Swagger Documentation** - Interactive API docs at `/docs` with complete examples
- ✅ **Multi-tenant Support** - Database and schema-level isolation
- ✅ **Permissions System** - Read-only and read-write access control
- ✅ **Audit Logging** - Track all operations for security
- ✅ **Azure Ready** - Optimized for Azure App Service deployment

## 📦 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL database on Azure
- Azure CLI (for deployment)
- Git

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd vibe-coding-backend
```

2. **Set up virtual environment and install dependencies**
```bash
# Option 1: Use the automated setup script (Recommended)
chmod +x setup.sh
./setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

Required environment variables:
- `MASTER_DB_URL`: PostgreSQL connection string for master database
- `AZURE_DB_HOST`: Azure PostgreSQL host
- `ENCRYPTION_KEY`: 256-bit encryption key (will be generated if not provided)
- `API_KEY_SALT`: Salt for API key hashing

4. **Initialize the database**
```bash
python scripts/init_db.py
```

This will:
- Create all required tables in the master database
- Generate a sample user and API key
- Set up initial permissions

Save the generated API key - it cannot be retrieved again!

5. **Start the API server**
```bash
# Start the FastAPI server
python main.py
```

The server will be available at:
- 🌐 **API**: http://localhost:8000
- 📚 **Swagger UI**: http://localhost:8000/docs
- 📖 **ReDoc**: http://localhost:8000/redoc
- 📋 **OpenAPI Spec**: http://localhost:8000/openapi.json

## 🚀 Deployment

### Azure App Service (Recommended)

This backend is optimized for Azure App Service, providing seamless integration with Azure PostgreSQL.

#### Quick Deploy
```bash
# Login to Azure
az login

# Create and deploy (first time)
az webapp up \
  --resource-group vibe-coding-rg \
  --name vibe-coding-backend \
  --runtime "PYTHON:3.11" \
  --sku B1
```

#### GitHub Actions CI/CD
1. Push to GitHub
2. Set up GitHub Actions with Azure publish profile
3. Push to main branch for automatic deployment

See [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md) for complete deployment instructions.

## 🧪 Testing the API

### Run Complete Test Suite

```bash
# Test all endpoints with the default database
python test_complete.py

# Test with a specific database
python test_complete.py your_database_name
```

### Test Individual Endpoints

```bash
# Test authentication
curl -X POST http://localhost:8000/api/auth/validate \
  -H "X-API-Key: vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA" \
  -H "Content-Type: application/json"

# Create a table
curl -X POST http://localhost:8000/api/tables \
  -H "X-API-Key: vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "user_db_001",
    "schema": "public", 
    "table": "products",
    "columns": [
      {"name": "id", "type": "SERIAL", "constraints": ["PRIMARY KEY"]},
      {"name": "name", "type": "VARCHAR(100)", "constraints": ["NOT NULL"]},
      {"name": "price", "type": "DECIMAL(10,2)"}
    ]
  }'

# Insert data
curl -X POST http://localhost:8000/api/data/public/products \
  -H "X-API-Key: vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "user_db_001",
    "data": {"name": "Laptop", "price": 999.99}
  }'

# Query data
curl -X GET "http://localhost:8000/api/data/public/products?database=user_db_001" \
  -H "X-API-Key: vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"
```

## 📊 Using Swagger UI

1. Start the server: `python main.py`
2. Open http://localhost:8000/docs
3. Click the "Authorize" button (🔒)
4. Enter your API key: `vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA`
5. Try any endpoint interactively!

## 📝 Available API Endpoints

### System
- `GET /api/health` - Health check (no auth required)

### Authentication
- `POST /api/auth/validate` - Validate API key and get user info
- `GET /api/auth/permissions` - Get user's permissions

### Table Operations (DDL)
- `POST /api/tables` - Create a new table
- `GET /api/tables` - List all tables in a schema
- `GET /api/tables/{table}/structure` - Get table structure/columns
- `DELETE /api/tables/{table}` - Drop a table

### Data Operations (DML)
- `GET /api/data/{schema}/{table}` - Query data with filtering and pagination
- `POST /api/data/{schema}/{table}` - Insert single or multiple records
- `PUT /api/data/{schema}/{table}` - Update records
- `DELETE /api/data/{schema}/{table}` - Delete records

### Raw SQL Query
- `POST /api/query` - Execute raw SQL with safety controls

## Usage Examples

### Python Example

```python
import requests

# Configuration
api_key = "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA"  # Your API key
base_url = "http://localhost:8000"  # Or your Azure URL
headers = {"X-API-Key": api_key}

# 1. Validate API key
response = requests.post(f"{base_url}/api/auth/validate", headers=headers)
print(f"User info: {response.json()}")

# 2. Create a table
create_table = {
    "database": "user_db_001",
    "schema": "public",
    "table": "users",
    "columns": [
        {"name": "id", "type": "SERIAL", "constraints": ["PRIMARY KEY"]},
        {"name": "email", "type": "VARCHAR(255)", "constraints": ["UNIQUE", "NOT NULL"]},
        {"name": "name", "type": "VARCHAR(100)"},
        {"name": "created_at", "type": "TIMESTAMP", "default": "NOW()"}
    ]
}
response = requests.post(f"{base_url}/api/tables", json=create_table, headers=headers)
print(f"Table created: {response.json()}")

# 3. Insert data (single record)
insert_single = {
    "database": "user_db_001",
    "data": {"email": "john@example.com", "name": "John Doe"},
    "returning": ["id", "created_at"]
}
response = requests.post(f"{base_url}/api/data/public/users", json=insert_single, headers=headers)
print(f"Inserted: {response.json()}")

# 4. Insert bulk data
insert_bulk = {
    "database": "user_db_001",
    "data": [
        {"email": "jane@example.com", "name": "Jane Smith"},
        {"email": "bob@example.com", "name": "Bob Johnson"}
    ]
}
response = requests.post(f"{base_url}/api/data/public/users", json=insert_bulk, headers=headers)
print(f"Bulk inserted: {response.json()}")

# 5. Query data with filtering
params = {
    "database": "user_db_001",
    "where": '{"name": "John Doe"}',  # JSON string for WHERE conditions
    "limit": 10
}
response = requests.get(f"{base_url}/api/data/public/users", params=params, headers=headers)
print(f"Query result: {response.json()}")

# 6. Update data
update_data = {
    "database": "user_db_001",
    "set": {"name": "John Updated"},
    "where": {"email": "john@example.com"}
}
response = requests.put(f"{base_url}/api/data/public/users", json=update_data, headers=headers)
print(f"Updated: {response.json()}")

# 7. Execute raw SQL with typed parameters
raw_query = {
    "database": "user_db_001",
    "query": "SELECT * FROM public.users WHERE created_at > $1 AND name LIKE $2 LIMIT $3",
    "params": [
        {"value": "2024-01-01", "type": "date"},
        {"value": "%John%", "type": "string"},
        {"value": "10", "type": "integer"}
    ],
    "read_only": True
}
response = requests.post(f"{base_url}/api/query", json=raw_query, headers=headers)
print(f"Raw query result: {response.json()}")

# 8. Delete data
delete_data = {
    "database": "user_db_001",
    "where": {"email": "bob@example.com"}
}
response = requests.delete(f"{base_url}/api/data/public/users", json=delete_data, headers=headers)
print(f"Deleted: {response.json()}")
```

### JavaScript/TypeScript Example

```javascript
const API_KEY = 'vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA';
const BASE_URL = 'http://localhost:8000';

// Helper function for API calls
async function apiCall(endpoint, method = 'GET', body = null, params = null) {
  const url = new URL(`${BASE_URL}${endpoint}`);
  
  if (params) {
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
  }
  
  const options = {
    method,
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    }
  };
  
  if (body) {
    options.body = JSON.stringify(body);
  }
  
  const response = await fetch(url, options);
  return response.json();
}

// Example usage
async function examples() {
  // Create table
  const table = await apiCall('/api/tables', 'POST', {
    database: 'user_db_001',
    schema: 'public',
    table: 'products',
    columns: [
      { name: 'id', type: 'SERIAL', constraints: ['PRIMARY KEY'] },
      { name: 'name', type: 'VARCHAR(100)', constraints: ['NOT NULL'] },
      { name: 'price', type: 'DECIMAL(10,2)' },
      { name: 'stock', type: 'INTEGER', default: '0' }
    ]
  });
  
  // Insert data
  const inserted = await apiCall('/api/data/public/products', 'POST', {
    database: 'user_db_001',
    data: { name: 'Laptop', price: 999.99, stock: 10 }
  });
  
  // Query data
  const products = await apiCall('/api/data/public/products', 'GET', null, {
    database: 'user_db_001',
    limit: 10,
    order_by: 'price',
    order: 'DESC'
  });
  
  // Update data
  const updated = await apiCall('/api/data/public/products', 'PUT', {
    database: 'user_db_001',
    set: { stock: 5 },
    where: { name: 'Laptop' }
  });
  
  // Raw SQL query with typed parameters
  const stats = await apiCall('/api/query', 'POST', {
    database: 'user_db_001',
    query: 'SELECT COUNT(*) as total FROM public.products WHERE created_at > $1 AND price > $2',
    params: [
      { value: '2024-01-01', type: 'date' },
      { value: '100', type: 'float' }
    ],
    read_only: true
  });
  
  console.log({ table, inserted, products, updated, stats });
}

examples();
```

## Raw SQL Query Endpoint

The `/api/query` endpoint allows execution of raw SQL queries with proper parameterization and type safety.

### Parameter Types

All query parameters must include type information to ensure proper conversion for PostgreSQL:

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text values | `{"value": "John Doe", "type": "string"}` |
| `integer` | Whole numbers | `{"value": "42", "type": "integer"}` |
| `float` | Decimal numbers | `{"value": "99.99", "type": "float"}` |
| `boolean` | True/False | `{"value": "true", "type": "boolean"}` |
| `date` | Date only | `{"value": "2024-01-01", "type": "date"}` |
| `timestamp` | Date and time | `{"value": "2024-01-01 14:30:00", "type": "timestamp"}` |
| `json` | JSON data | `{"value": "{\"key\": \"value\"}", "type": "json"}` |

### Query Examples

#### Simple Query with Date Parameter
```bash
curl -X POST http://localhost:8000/api/query \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "user_db_001",
    "query": "SELECT * FROM users WHERE created_at > $1",
    "params": [
      {"value": "2024-01-01", "type": "date"}
    ],
    "read_only": true
  }'
```

#### Complex Query with Multiple Types
```bash
curl -X POST http://localhost:8000/api/query \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "user_db_001",
    "query": "SELECT * FROM orders WHERE created_at BETWEEN $1 AND $2 AND amount > $3 AND active = $4",
    "params": [
      {"value": "2024-01-01", "type": "timestamp"},
      {"value": "2024-12-31 23:59:59", "type": "timestamp"},
      {"value": "100.50", "type": "float"},
      {"value": "true", "type": "boolean"}
    ],
    "read_only": true
  }'
```

### Important Notes

- All parameters require both `value` and `type` fields
- Use parameterized queries ($1, $2, etc.) to prevent SQL injection
- Set `read_only: true` for SELECT queries to enforce read-only access
- Maximum query timeout is 60 seconds
- Certain operations (DROP DATABASE, CREATE USER, etc.) are blocked for security

## Project Structure

```
vibe-coding-backend/
├── api/                    # API endpoints
│   ├── auth/              # Authentication endpoints
│   ├── data/              # Data CRUD operations
│   ├── tables/            # Table management
│   └── schemas/           # Schema management
├── lib/                   # Core libraries
│   ├── auth.py           # Authentication logic
│   ├── database.py       # Database connection management
│   ├── permissions.py    # Permission checking
│   └── logging.py        # Logging and auditing
├── schemas/              # Pydantic models
│   ├── requests.py      # Request models
│   └── responses.py     # Response models
├── scripts/              # Utility scripts
│   ├── init_db.sql      # Database schema
│   └── init_db.py       # Database initialization
├── requirements.txt      # Python dependencies
├── startup.sh           # Azure startup script
└── CLAUDE.md            # Detailed project documentation
```

## Security

- All database connections are encrypted
- API keys are hashed before storage
- SQL injection prevention via parameterized queries
- Query timeout limits and resource controls
- Comprehensive audit logging
- Schema-level access control

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=lib --cov=api --cov-report=html
```

## Development

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Monitoring

The system logs all API operations to the audit_logs table. You can query logs via:
- `/api/admin/logs` endpoint
- Direct database queries on the master database

## User & Database Management

### Admin Console (Interactive)

The easiest way to manage users is through the interactive admin console:

```bash
source venv/bin/activate
python scripts/admin.py --interactive
```

This provides a menu-driven interface for all operations:
- Create Users
- Generate API Keys  
- Assign Databases
- Grant/Revoke Permissions
- List Users & Permissions
- Activate/Deactivate Users

### Command Line Management

#### Create a New User

```bash
# Create user
python scripts/admin.py --create-user "developer@company.com" --org "Development Team"

# Generate API key
python scripts/admin.py --generate-key "developer@company.com" --key-name "Dev API Key" --env dev
```

**⚠️ IMPORTANT: Save the API key immediately - it cannot be retrieved again!**

#### Assign Database to User

```bash
# Assign database with connection string
python scripts/admin.py --assign-db "developer@company.com" "user_db_001" \
  "postgresql://username:password@host:5432/database?sslmode=require"

# For Azure PostgreSQL
python scripts/admin.py --assign-db "developer@company.com" "user_db_001" \
  "postgresql://user@server:password@server.postgres.database.azure.com:5432/db?sslmode=require"
```

#### Grant Permissions

```bash
# Grant read-write access to public schema
python scripts/admin.py --grant "developer@company.com" "user_db_001" "public" "read_write"

# Grant read-only access to reports schema  
python scripts/admin.py --grant "developer@company.com" "user_db_001" "reports" "read_only"
```

#### View Users and Permissions

```bash
# List all users
python scripts/admin.py --list-users

# View all permissions
python scripts/admin.py --list-permissions

# View specific user's permissions
python scripts/admin.py --list-permissions "developer@company.com"
```

### Complete Setup Example

Setting up a new user for Lovable/Claude Code platforms:

```bash
# 1. Create the user
python scripts/admin.py --create-user "project1@lovable.app" --org "Lovable Project 1"

# 2. Generate API key
python scripts/admin.py --generate-key "project1@lovable.app" --key-name "Production Key" --env prod
# Output: vibe_prod_xxxxxxxxxxxxx (SAVE THIS!)

# 3. Create database in Azure PostgreSQL
# Use Azure Portal or CLI to create the database first

# 4. Assign database to user
python scripts/admin.py --assign-db "project1@lovable.app" "project1_db" \
  "postgresql://project1user@vibe-coding:MyPassword@vibe-coding.postgres.database.azure.com:5432/project1_db?sslmode=require"

# 5. Grant permissions
python scripts/admin.py --grant "project1@lovable.app" "project1_db" "public" "read_write"

# 6. Test the API key
curl -X POST http://localhost:8000/api/auth/validate \
  -H "X-API-Key: vibe_prod_xxxxxxxxxxxxx" \
  -H "Content-Type: application/json"
```

### Multi-Tenant Setup

For multiple isolated customers:

```bash
# Customer A
python scripts/admin.py --create-user "customer_a@app.com" --org "Customer A"
python scripts/admin.py --generate-key "customer_a@app.com" --key-name "Customer A API"
python scripts/admin.py --assign-db "customer_a@app.com" "customer_a_db" \
  "postgresql://user:pass@host:5432/customer_a_db?sslmode=require"
python scripts/admin.py --grant "customer_a@app.com" "customer_a_db" "public" "read_write"

# Customer B (with read-only access)
python scripts/admin.py --create-user "customer_b@app.com" --org "Customer B"
python scripts/admin.py --generate-key "customer_b@app.com" --key-name "Customer B API"
python scripts/admin.py --assign-db "customer_b@app.com" "customer_b_db" \
  "postgresql://user:pass@host:5432/customer_b_db?sslmode=require"
python scripts/admin.py --grant "customer_b@app.com" "customer_b_db" "public" "read_only"
```

### Permission Levels

- **`read_only`**: User can only SELECT data
- **`read_write`**: User can perform all operations (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, etc.)

### Bulk User Setup

For setting up multiple users at once, see `scripts/setup_example_users.py`:

```bash
python scripts/setup_example_users.py
```

### Administrative Operations

```bash
# Revoke permission (use interactive mode)
python scripts/admin.py --interactive
# Select option 7: Revoke Permission

# Deactivate a user (disables account and all API keys)
python scripts/admin.py --interactive
# Select option 8: Deactivate User

# Reactivate a user
python scripts/admin.py --interactive
# Select option 9: Activate User
```

## Troubleshooting

### Database Connection Issues
- Ensure Azure PostgreSQL firewall rules allow connections
- Verify SSL mode is set to 'require' for Azure
- Check connection string format in MASTER_DB_URL
- Test connection: `psql "postgresql://connection_string_here"`

### API Key Issues
- API keys must be passed in the `X-API-Key` header (not as URL parameters)
- Keys are prefixed with `vibe_[environment]_`
- Check key hasn't expired or been revoked
- Verify user is active: `python scripts/admin.py --list-users`

### Query Parameter Type Errors
- For date/timestamp parameters, always specify the type:
  ```json
  {"value": "2024-01-01", "type": "date"}
  ```
- Common types: `string`, `integer`, `float`, `boolean`, `date`, `timestamp`
- All parameters in `/api/query` require both `value` and `type` fields

### Permission Errors
- Verify user has appropriate permissions on the schema
- Check database assignment is active
- Review permissions: `python scripts/admin.py --list-permissions "email"`
- Check audit logs in the database for detailed error information

### User Can't Access Database

1. Verify user is active:
```bash
python scripts/admin.py --list-users
```

2. Check permissions:
```bash
python scripts/admin.py --list-permissions "user@example.com"
```

3. Verify database exists and is accessible:
```bash
psql "postgresql://connection_string_from_database_assignments"
```

## Documentation

- **[USER_MANAGEMENT.md](USER_MANAGEMENT.md)** - Detailed user management guide
- **[README_DEPLOYMENT.md](README_DEPLOYMENT.md)** - Deployment instructions
- **[CLAUDE.md](CLAUDE.md)** - Complete project documentation

## License

[Your License Here]

## Support

For issues and questions, please contact support@your-domain.com