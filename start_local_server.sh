#!/bin/bash

echo "=========================================="
echo "STARTING LOCAL BACKEND SERVER"
echo "=========================================="

# Kill any existing server on port 8000
echo "Stopping any existing server on port 8000..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
sleep 2

# Start the server in background
echo "Starting server on http://localhost:8000..."
nohup python3 run_local_server.py > server.log 2>&1 &
SERVER_PID=$!

echo "Server PID: $SERVER_PID"
echo "Logs: tail -f server.log"

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if curl -s http://localhost:8000/api/auth/permissions -o /dev/null -w "%{http_code}" | grep -q "401"; then
    echo "✅ Server is running!"
    echo ""
    echo "Test with: ./test_local_backend.sh"
    echo "Stop with: pkill -f 'uvicorn.*8000'"
else
    echo "❌ Server failed to start. Check server.log for errors"
    exit 1
fi