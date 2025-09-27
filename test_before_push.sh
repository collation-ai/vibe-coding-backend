#!/bin/bash

echo "====================================="
echo "Pre-Push Validation Script"
echo "====================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any tests fail
FAILED=0

# 1. Check Black formatting
echo "1. Checking code formatting with Black..."
if python3 -m black --check lib/ api/ schemas/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Black formatting check passed${NC}"
else
    echo -e "${RED}✗ Black formatting check failed${NC}"
    echo -e "${YELLOW}  Run: python3 -m black lib/ api/ schemas/${NC}"
    FAILED=1
fi

# 2. Check Flake8 linting
echo ""
echo "2. Checking code quality with Flake8..."
if python3 -m flake8 lib/ api/ schemas/ --max-line-length=100 --ignore=E203,W503 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Flake8 linting check passed${NC}"
else
    echo -e "${RED}✗ Flake8 linting check failed${NC}"
    echo -e "${YELLOW}  Run: python3 -m flake8 lib/ api/ schemas/ --max-line-length=100 --ignore=E203,W503${NC}"
    python3 -m flake8 lib/ api/ schemas/ --max-line-length=100 --ignore=E203,W503
    FAILED=1
fi

# 3. Test local server startup
echo ""
echo "3. Testing local server startup..."
if timeout 5 python3 run_local.py > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Server timeout (expected)${NC}"
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo -e "${GREEN}✓ Server starts successfully${NC}"
    else
        echo -e "${RED}✗ Server failed to start (exit code: $EXIT_CODE)${NC}"
        FAILED=1
    fi
fi

# 4. Check for common issues
echo ""
echo "4. Checking for common issues..."

# Check for debugging print statements
if grep -r "print(" lib/ api/ schemas/ --include="*.py" | grep -v "#" > /dev/null; then
    echo -e "${YELLOW}⚠ Found print statements (consider using logger instead)${NC}"
    grep -r "print(" lib/ api/ schemas/ --include="*.py" | grep -v "#"
else
    echo -e "${GREEN}✓ No print statements found${NC}"
fi

# Check for TODO comments
if grep -r "TODO" lib/ api/ schemas/ --include="*.py" > /dev/null; then
    echo -e "${YELLOW}⚠ Found TODO comments${NC}"
    grep -r "TODO" lib/ api/ schemas/ --include="*.py"
else
    echo -e "${GREEN}✓ No TODO comments found${NC}"
fi

# Summary
echo ""
echo "====================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Safe to push.${NC}"
    echo "====================================="
    exit 0
else
    echo -e "${RED}Some checks failed! Please fix before pushing.${NC}"
    echo "====================================="
    exit 1
fi