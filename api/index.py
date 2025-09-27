"""
Vercel Python Serverless Function Handler for FastAPI
"""
import sys
import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastAPI app and dependencies
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app

# Create a test client for the FastAPI app
client = TestClient(app)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        # Handle root path
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <html>
                <head><title>Vibe Coding Backend API</title></head>
                <body>
                    <h1>Vibe Coding Backend API</h1>
                    <p>API is running successfully!</p>
                    <p>Available endpoints:</p>
                    <ul>
                        <li><a href="/api/health">/api/health</a> - Health check</li>
                        <li>/api/auth/validate - Validate API key</li>
                        <li>/api/auth/permissions - Get permissions</li>
                        <li>/api/tables - Table operations</li>
                        <li>/api/data - Data operations</li>
                        <li>/api/query - Raw SQL queries</li>
                    </ul>
                    <p>For full API documentation, use Swagger UI locally.</p>
                </body>
            </html>
            """
            self.wfile.write(html.encode())
            return
        
        # Forward to FastAPI
        headers = dict(self.headers)
        response = client.get(parsed_path.path, headers=headers)
        
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in ['content-length', 'content-encoding']:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)
        
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        
        # Read request body
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Parse JSON body if content type is JSON
        content_type = self.headers.get('Content-Type', '')
        if 'application/json' in content_type and body:
            try:
                json_body = json.loads(body.decode('utf-8'))
            except:
                json_body = None
        else:
            json_body = None
        
        # Forward to FastAPI
        headers = dict(self.headers)
        
        if json_body is not None:
            response = client.post(parsed_path.path, json=json_body, headers=headers)
        elif body:
            response = client.post(parsed_path.path, data=body, headers=headers)
        else:
            response = client.post(parsed_path.path, headers=headers)
        
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in ['content-length', 'content-encoding']:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)
        
    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        
        # Read request body
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Parse JSON body if content type is JSON
        content_type = self.headers.get('Content-Type', '')
        if 'application/json' in content_type and body:
            try:
                json_body = json.loads(body.decode('utf-8'))
            except:
                json_body = None
        else:
            json_body = None
        
        # Forward to FastAPI
        headers = dict(self.headers)
        
        if json_body is not None:
            response = client.put(parsed_path.path, json=json_body, headers=headers)
        elif body:
            response = client.put(parsed_path.path, data=body, headers=headers)
        else:
            response = client.put(parsed_path.path, headers=headers)
        
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in ['content-length', 'content-encoding']:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)
        
    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        
        # Forward to FastAPI
        headers = dict(self.headers)
        response = client.delete(parsed_path.path, headers=headers)
        
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in ['content-length', 'content-encoding']:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)
        
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key')
        self.send_header('Content-Length', '0')
        self.end_headers()