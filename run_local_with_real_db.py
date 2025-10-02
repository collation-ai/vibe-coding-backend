#!/usr/bin/env python3
"""
Run the API locally with REAL database connection
This allows testing before deploying to Azure
"""

import os
import sys
from pathlib import Path

# Load real environment variables from .env
from dotenv import load_dotenv

env_file = Path(".env")
if env_file.exists():
    print(f"Loading REAL environment from {env_file}")
    load_dotenv(env_file, override=True)
else:
    print("ERROR: .env file not found!")
    sys.exit(1)

# Verify we have the real database connection
if "azure.com" not in os.environ.get("MASTER_DB_URL", ""):
    print("ERROR: Not using real Azure database!")
    sys.exit(1)

print("=" * 60)
print("Starting LOCAL server with REAL DATABASE")
print("=" * 60)
print(f"Database: {os.environ['MASTER_DB_URL'].split('@')[1].split('/')[0]}")
print(f"Encryption: {'SET' if os.environ.get('ENCRYPTION_KEY') else 'NOT SET'}")
print(f"API Salt: {'SET' if os.environ.get('API_KEY_SALT') else 'NOT SET'}")
print("=" * 60)

# Now import and run the FastAPI app
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create main app
app = FastAPI(title="Vibe Backend - LOCAL with REAL DB")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import the actual endpoint functions directly
from api.auth.validate import get_permissions, validate_api_key
from api.query import execute_raw_query

# Add the routes directly
app.add_api_route("/api/auth/permissions", get_permissions, methods=["GET"])
app.add_api_route("/api/auth/validate", validate_api_key, methods=["POST"])
app.add_api_route("/api/query", execute_raw_query, methods=["POST"])

if __name__ == "__main__":
    print("\nServer starting on http://localhost:8000")
    print("\nTest endpoints:")
    print("  http://localhost:8000/api/auth/permissions")
    print("  http://localhost:8000/api/query")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
