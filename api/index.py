"""
Vercel serverless function entry point
Handles all API routes for Vercel deployment
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import main app
from main import app

# Create handler for Vercel
handler = Mangum(app)

# Export handler for Vercel
def main(request, context):
    return handler(request, context)