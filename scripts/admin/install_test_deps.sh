#!/bin/bash
# Install test dependencies including PyJWT

# Set up error handling
set -e

echo "Installing Python test dependencies..."
pip install -r requirements-dev.txt

echo "Checking if PyJWT is installed correctly..."
python -c "import jwt; print(f'PyJWT version {jwt.__version__} installed successfully')"

echo "Done! You can now run tests with: npm run test"