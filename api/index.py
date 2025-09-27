from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        path = self.path

        # Simple routing for testing
        if path == "/" or path == "/api":
            response = {"message": "Vibe Coding Backend API", "status": "running"}
        elif path == "/api/health":
            # Import here to avoid issues during class definition
            from api.health import health_check
            import asyncio

            # Run the async health check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(health_check())
                response = result.dict() if hasattr(result, "dict") else result
            finally:
                loop.close()
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response, default=str).encode())

    def do_POST(self):
        """Handle POST requests"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps({"message": "POST endpoint", "path": self.path}).encode()
        )
