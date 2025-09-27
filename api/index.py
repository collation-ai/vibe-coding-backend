"""
Vercel serverless function entry point
Handles all API routes for Vercel deployment
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export the FastAPI app directly for Vercel
app = app