#!/bin/bash

# Setup script for Vibe Coding Backend

echo "======================================"
echo "Vibe Coding Backend Setup"
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Python 3.9+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your database credentials"
else
    echo "✅ .env file already exists"
fi

# Generate encryption key if not set
if ! grep -q "ENCRYPTION_KEY=" .env || grep -q "ENCRYPTION_KEY=your-256-bit-encryption-key-here" .env; then
    echo "Generating encryption key..."
    encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        sed -i '' "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$encryption_key|" .env
    else
        # Linux
        sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$encryption_key|" .env
    fi
    echo "✅ Encryption key generated and saved to .env"
fi

# Generate API key salt if not set
if ! grep -q "API_KEY_SALT=" .env || grep -q "API_KEY_SALT=your-salt-for-hashing-api-keys" .env; then
    echo "Generating API key salt..."
    api_salt=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        sed -i '' "s|API_KEY_SALT=.*|API_KEY_SALT=$api_salt|" .env
    else
        # Linux
        sed -i "s|API_KEY_SALT=.*|API_KEY_SALT=$api_salt|" .env
    fi
    echo "✅ API key salt generated and saved to .env"
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Azure PostgreSQL credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python scripts/init_db.py"
echo "4. For local development: vercel dev"
echo "5. For deployment: Connect to GitHub and deploy via Vercel dashboard"
echo ""
