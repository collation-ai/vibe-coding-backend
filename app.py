"""
Azure App Service entry point
This file is used by Azure to start the application
"""

from main import app

# Azure App Service looks for an 'app' or 'application' variable
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)