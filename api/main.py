"""
Vercel serverless function handler
"""

import sys
import os
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastAPI app
from main import app

# Import Vercel's serverless adapter
from mangum import Mangum

# Create the handler
handler = Mangum(app, lifespan="off")

def main(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler function for Vercel
    """
    return handler(event, context)