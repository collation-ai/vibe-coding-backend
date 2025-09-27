"""
Vercel API Handler
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Import FastAPI app
from main import app

# Export for Vercel
app = app