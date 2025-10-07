#!/bin/bash
# Start server script - uses .env file values by unsetting conflicting environment variables

cd /home/tanmais/vibe-coding-backend

# Unset environment variables that might override .env file
unset ENCRYPTION_KEY
unset API_KEY_SALT
unset MASTER_DB_URL

# Stop any existing server
pkill -f "python3 main.py" 2>/dev/null || true

# Wait for process to stop
sleep 2

# Start the server (will load from .env file)
echo "Starting Vibe Coding Backend..."
echo "Loading configuration from .env file..."
nohup python3 main.py > server.log 2>&1 &

# Wait for server to start
sleep 3

# Check if server started successfully
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Server started successfully on http://localhost:8000"
    echo "📊 Admin Dashboard: http://localhost:8000/admin"
    echo "📚 API Docs: http://localhost:8000/docs"
else
    echo "❌ Server failed to start. Check server.log for details:"
    tail -20 server.log
fi
