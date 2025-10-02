#!/usr/bin/env python3
"""
Setup API Keys for Vibe Coding Backend
This script properly creates API keys in the database with correct hashing
"""

import hashlib
import psycopg2
from psycopg2 import sql
import uuid
import sys


def hash_api_key(api_key):
    """Hash an API key using SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def setup_api_keys(connection_string):
    """Setup the default API keys in the database"""

    # API keys to set up
    api_keys = [
        {
            "key": "vibe_dev_s645CftsZWQ1ZSqwNJMNzGsJV1QpYNnA",
            "email": "dev@vibe-coding.com",
            "username": "dev_api",
            "organization": "Vibe Coding Dev",
            "key_prefix": "vibe_dev",
            "name": "Development API Key",
        },
        {
            "key": "vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ",
            "email": "prod@vibe-coding.com",
            "username": "prod_api",
            "organization": "Vibe Coding Prod",
            "key_prefix": "vibe_prod",
            "name": "Production API Key",
        },
    ]

    try:
        # Connect to database
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()

        print("Connected to database successfully")

        for api_key_data in api_keys:
            # First, create or update the user
            cur.execute(
                """
                INSERT INTO users (email, username, organization, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    organization = EXCLUDED.organization,
                    updated_at = NOW()
                RETURNING id
            """,
                (
                    api_key_data["email"],
                    api_key_data["username"],
                    api_key_data["organization"],
                    True,
                ),
            )

            user_id = cur.fetchone()[0]
            print(f"Created/Updated user: {api_key_data['email']} (ID: {user_id})")

            # Hash the API key
            key_hash = hash_api_key(api_key_data["key"])

            # Insert or update the API key
            cur.execute(
                """
                INSERT INTO api_keys (user_id, key_hash, key_prefix, name, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (key_hash) 
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    last_used_at = NOW()
                RETURNING id
            """,
                (
                    user_id,
                    key_hash,
                    api_key_data["key_prefix"],
                    api_key_data["name"],
                    True,
                ),
            )

            api_key_id = cur.fetchone()[0]
            print(
                f"Created/Updated API key: {api_key_data['name']} (Prefix: {api_key_data['key_prefix']})"
            )

            # Add default permissions (optional)
            # You can modify this to add specific database assignments and permissions

        # Commit the transaction
        conn.commit()
        print("\n✅ API keys setup completed successfully!")

        # Display the API keys for reference
        print("\n📋 Your API Keys:")
        print("-" * 50)
        for key_data in api_keys:
            print(f"{key_data['name']}:")
            print(f"  Key: {key_data['key']}")
            print(f"  Email: {key_data['email']}")
            print()

        # Verify the setup
        cur.execute(
            """
            SELECT u.email, u.username, ak.key_prefix, ak.name, ak.is_active
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            ORDER BY u.email
        """
        )

        print("📊 Database Verification:")
        print("-" * 50)
        for row in cur.fetchall():
            email, username, prefix, name, is_active = row
            status = "✅ Active" if is_active else "❌ Inactive"
            print(f"{email} ({username}): {name} [{prefix}] - {status}")

        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=== Vibe Coding Backend - API Key Setup ===\n")

    # Get database connection string
    connection_string = input(
        "Enter your PostgreSQL connection string:\n(Format: postgresql://user:pass@host:5432/database?sslmode=require)\n> "
    )

    if not connection_string:
        print("❌ Connection string is required")
        sys.exit(1)

    setup_api_keys(connection_string)

    print("\n✅ Setup complete! You can now use these API keys to access the backend.")
    print("\nTo test:")
    print('curl -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \\')
    print("     https://vibe-coding-backend.azurewebsites.net/api/health")
