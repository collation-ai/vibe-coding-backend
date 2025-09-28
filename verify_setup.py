#!/usr/bin/env python3
"""Verify that the setup is complete and working"""

import sys
import os


def check_import(module_name):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        return True, "✅"
    except ImportError as e:
        return False, f"❌ {str(e)}"


def main():
    print("=" * 50)
    print("Verifying Vibe Coding Backend Setup")
    print("=" * 50)

    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(
        f"Python Version: {python_version} {'✅' if sys.version_info >= (3, 9) else '❌'}"
    )

    # Check critical imports
    modules = [
        "fastapi",
        "uvicorn",
        "asyncpg",
        "pydantic",
        "cryptography",
        "structlog",
        "dotenv",
    ]

    print("\nChecking dependencies:")
    all_good = True
    for module in modules:
        status, icon = check_import(module)
        print(f"  {module}: {icon}")
        if not status:
            all_good = False

    # Check if .env file exists
    print("\nConfiguration:")
    if os.path.exists(".env"):
        print("  .env file: ✅")
    else:
        print("  .env file: ❌ (Run: cp .env.example .env)")
        all_good = False

    # Check if we can import our modules
    print("\nChecking project modules:")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lib import config

        print("  lib.config: ✅")
    except Exception as e:
        print(f"  lib.config: ❌ {str(e)}")
        all_good = False

    print("\n" + "=" * 50)
    if all_good:
        print("✅ Setup verification PASSED!")
        print("\nNext steps:")
        print("1. Edit .env file with your Azure PostgreSQL credentials")
        print("2. Run: python scripts/init_db.py")
        print("3. For local development: vercel dev")
    else:
        print("❌ Setup verification FAILED!")
        print("\nPlease fix the issues above before proceeding.")
    print("=" * 50)


if __name__ == "__main__":
    main()
