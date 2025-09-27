#!/bin/bash

echo "Running local lint tests..."

# Run Black check
echo "=== Running Black formatter check ==="
python3 -m black --check lib/ api/ schemas/ --diff

# Run Flake8
echo -e "\n=== Running Flake8 linter ==="
python3 -m flake8 lib/ api/ schemas/ --max-line-length=100 --ignore=E203,W503

echo -e "\nDone! Fix any issues above before pushing."