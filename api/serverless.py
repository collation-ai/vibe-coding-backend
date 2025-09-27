"""
Vercel Serverless Function Handler
This is the main entry point for Vercel deployment
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path to import our app
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Now import the FastAPI app
from main import app

# Import the serverless handler
from mangum import Mangum

# Create the handler with specific settings for Vercel
handler = Mangum(
    app,
    lifespan="off",  # Disable lifespan for serverless
    api_gateway_base_path="/api"
)

# The main handler function that Vercel will call
def handler_function(event, context):
    """
    Main handler for Vercel Serverless Function
    """
    return handler(event, context)