#!/bin/bash

# Generate a new admin API key directly in the database

# Database connection
DB_URL="postgresql://vibecodingadmin:LiWTaaGcExgKZ4ULoA@vibe-coding.postgres.database.azure.com:5432/master_db?sslmode=require"

# Generate API key
API_KEY="vibe_prod_$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"

# Hash the key
API_KEY_SALT="7GcyvOMC7BH8k4IZ76GYnub7IOzcYU4b9P+VimRLi7E="
KEY_HASH=$(echo -n "${API_KEY}${API_KEY_SALT}" | sha256sum | awk '{print $1}')

# Get or create admin user
USER_ID=$(psql "$DB_URL" -t -c "SELECT id FROM users WHERE email = 'tanmais@example.com';")

if [ -z "$USER_ID" ]; then
    echo "Creating admin user..."
    USER_ID=$(psql "$DB_URL" -t -c "INSERT INTO users (email, username, password_hash, organization, is_active) VALUES ('tanmais@example.com', 'tanmais', '\$2b\$12\$dummyhash', 'Vibe Admin', true) RETURNING id;")
    echo "✅ Created user: $USER_ID"
else
    echo "✅ Found existing user: $USER_ID"
fi

# Trim whitespace
USER_ID=$(echo $USER_ID | tr -d ' ')

# Insert API key
echo "Generating API key..."
psql "$DB_URL" -c "INSERT INTO api_keys (user_id, key_hash, key_prefix, name, is_active) VALUES ('$USER_ID', '$KEY_HASH', 'vibe_prod', 'Admin Dashboard Key', true);"

echo ""
echo "============================================================"
echo "🔑 NEW ADMIN API KEY GENERATED!"
echo "============================================================"
echo ""
echo "$API_KEY"
echo ""
echo "============================================================"
echo ""
echo "⚠️  IMPORTANT: Save this key securely!"
echo "   This is the only time you'll see it."
echo ""
echo "💡 Use this key to login to the admin dashboard at:"
echo "   http://localhost:8000/admin"
echo ""
