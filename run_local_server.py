#!/usr/bin/env python3
"""
Run the backend API locally for testing BEFORE deploying to Azure
This mimics the Azure backend completely
"""

import os
import sys

# Load environment variables from .env.local if it exists
from dotenv import load_dotenv
env_file = ".env.local"
if os.path.exists(env_file):
    print(f"Loading environment from {env_file}")
    load_dotenv(env_file)
else:
    print("WARNING: No .env.local file found. Using system environment variables.")
    
# Ensure required variables are set
if not os.environ.get("ENCRYPTION_KEY"):
    print("ERROR: ENCRYPTION_KEY not set. Create .env.local file with test values.")
    sys.exit(1)

print("Starting local backend server on port 8000...")
print("This server mimics the Azure backend exactly")
print("-" * 60)
print("Test endpoints:")
print("  http://localhost:8000/api/auth/permissions")
print("  http://localhost:8000/api/query")
print("-" * 60)

# Import and run the FastAPI apps
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create main app
app = FastAPI(title="Vibe Backend Local Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the auth endpoints
from api.auth.validate import app as auth_app
app.mount("/api/auth", auth_app)

# Mount the query endpoint
from api.query import app as query_app
app.mount("/api", query_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)