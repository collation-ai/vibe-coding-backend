#!/usr/bin/env python3
"""
Test environment variables for Vercel deployment
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

print("Checking environment variables...")
print("=" * 50)

required_vars = [
    "MASTER_DB_URL",
    "AZURE_DB_HOST", 
    "ENCRYPTION_KEY",
    "API_KEY_SALT"
]

missing = []
found = []

for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive data
        if "URL" in var or "KEY" in var or "SALT" in var:
            masked = value[:10] + "..." + value[-5:] if len(value) > 15 else "***"
            print(f"✓ {var}: {masked}")
        else:
            print(f"✓ {var}: {value}")
        found.append(var)
    else:
        print(f"✗ {var}: NOT SET")
        missing.append(var)

print("=" * 50)

if missing:
    print(f"\n❌ Missing {len(missing)} environment variable(s):")
    for var in missing:
        print(f"  - {var}")
    print("\nTo fix, set these in Vercel Dashboard or .env file")
    sys.exit(1)
else:
    print(f"\n✅ All {len(found)} required environment variables are set!")
    
    # Test database URL format
    db_url = os.getenv("MASTER_DB_URL")
    if db_url:
        if "postgresql://" in db_url or "postgres://" in db_url:
            print("✓ Database URL format looks correct")
        else:
            print("⚠ Database URL should start with postgresql:// or postgres://")
            
        if "sslmode=require" in db_url:
            print("✓ SSL mode is set (required for Azure)")
        else:
            print("⚠ Consider adding ?sslmode=require to the URL for Azure PostgreSQL")
    
    sys.exit(0)