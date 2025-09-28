#!/usr/bin/env python3
"""
Example script showing how to set up users with databases and permissions
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


async def setup_example_users():
    """Set up example users with databases and permissions"""

    # Import admin module
    from admin import AdminManager

    admin = AdminManager()

    print("=" * 60)
    print("SETTING UP EXAMPLE USERS")
    print("=" * 60)

    # Example 1: Create a developer with full access
    print("\n1. Creating Developer User...")
    dev_email = "developer@example.com"

    # Create user
    user_id = await admin.create_user(dev_email, "Development Team")

    # Generate API key
    api_key = await admin.generate_api_key(dev_email, "Development Key", "dev")

    # Assign database
    dev_db_url = "postgresql://dev_user:dev_pass@localhost:5432/dev_db?sslmode=require"
    await admin.assign_database(dev_email, "dev_db", dev_db_url)

    # Grant full permissions on public schema
    await admin.grant_permission(dev_email, "dev_db", "public", "read_write")

    print("\nDeveloper setup complete!")
    print(f"Email: {dev_email}")
    print(f"API Key: {api_key}")
    print("Database: dev_db (read_write on public schema)")

    # Example 2: Create a read-only analyst
    print("\n" + "=" * 60)
    print("2. Creating Analyst User...")
    analyst_email = "analyst@example.com"

    # Create user
    await admin.create_user(analyst_email, "Analytics Team")

    # Generate API key
    analyst_key = await admin.generate_api_key(
        analyst_email, "Analytics Key", "prod", expires_days=90
    )

    # Assign database
    analytics_db_url = "postgresql://analytics:analytics_pass@localhost:5432/analytics_db?sslmode=require"
    await admin.assign_database(analyst_email, "analytics_db", analytics_db_url)

    # Grant read-only permissions
    await admin.grant_permission(analyst_email, "analytics_db", "public", "read_only")
    await admin.grant_permission(analyst_email, "analytics_db", "reports", "read_only")

    print("\nAnalyst setup complete!")
    print(f"Email: {analyst_email}")
    print(f"API Key: {analyst_key}")
    print("Database: analytics_db (read_only on public and reports schemas)")

    # Example 3: Create a multi-database user
    print("\n" + "=" * 60)
    print("3. Creating Multi-Database User...")
    multi_email = "power_user@example.com"

    # Create user
    await admin.create_user(multi_email, "Power Users")

    # Generate API key
    multi_key = await admin.generate_api_key(multi_email, "Power User Key", "prod")

    # Assign multiple databases
    db1_url = "postgresql://user:pass@localhost:5432/app_db?sslmode=require"
    db2_url = "postgresql://user:pass@localhost:5432/reporting_db?sslmode=require"

    await admin.assign_database(multi_email, "app_db", db1_url)
    await admin.assign_database(multi_email, "reporting_db", db2_url)

    # Grant different permissions on different databases
    await admin.grant_permission(multi_email, "app_db", "public", "read_write")
    await admin.grant_permission(multi_email, "app_db", "private", "read_only")
    await admin.grant_permission(multi_email, "reporting_db", "public", "read_only")

    print("\nMulti-database user setup complete!")
    print(f"Email: {multi_email}")
    print(f"API Key: {multi_key}")
    print("Databases:")
    print("  - app_db: read_write on public, read_only on private")
    print("  - reporting_db: read_only on public")

    # Show all users and permissions
    print("\n" + "=" * 60)
    print("SUMMARY OF ALL USERS")
    print("=" * 60)

    await admin.list_users()
    await admin.list_permissions()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Save all API keys above - they cannot be retrieved again!")
    print("\nNote: Make sure the PostgreSQL databases referenced above exist")
    print("and are accessible before using the API.")


if __name__ == "__main__":
    asyncio.run(setup_example_users())
