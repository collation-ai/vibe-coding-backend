"""
Vercel serverless function handler
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastAPI app
from main import app

# Export app directly for Vercel
app = app