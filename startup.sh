#!/bin/bash

# Azure App Service startup script
echo "Starting Vibe Coding Backend API..."

# Install dependencies
pip install -r requirements.txt

# Start the application with Gunicorn
gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 600 --bind 0.0.0.0:8000 main:app