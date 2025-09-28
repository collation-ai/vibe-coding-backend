#!/usr/bin/env python3
"""Development server for testing the API locally"""

if __name__ == "__main__":
    import uvicorn
    import sys
    import os

    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("Starting Vibe Coding Backend Development Server")
    print("-" * 50)
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("OpenAPI: http://localhost:8000/openapi.json")
    print("-" * 50)
    print("Press CTRL+C to stop\n")

    # Run with string import for hot reload
    uvicorn.run(
        "run_local:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
