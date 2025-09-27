#!/usr/bin/env python3
"""Run the API locally for testing"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

# Import the complete app from main.py which has all endpoints
from main import app

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting Vibe Coding Backend API")
    print("="*60)
    print("\n📍 API Base URL: http://localhost:8000")
    print("📚 Swagger Docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("📋 OpenAPI Spec: http://localhost:8000/openapi.json")
    print("\n" + "="*60)
    print("✅ All endpoints are available!")
    print("🔐 Use the Authorize button in Swagger UI to add your API key")
    print("\nPress CTRL+C to stop the server")
    print("="*60 + "\n")
    
    # Use string import for reload to work
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
