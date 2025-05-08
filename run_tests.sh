#!/bin/bash
# Script to run the feature tests for the healthcare data sharing system

# Set up environment
echo "Setting up environment..."
export API_URL="http://localhost:8000/api"

# Check if the API is running
echo "Checking if the API is running..."
curl -s $API_URL/health > /dev/null
if [ $? -ne 0 ]; then
    echo "API is not running. Please start the API server first."
    echo "You can start it with: docker-compose up -d api"
    exit 1
fi

# Check if IPFS is running
echo "Checking if IPFS is running..."
curl -s http://localhost:5001/api/v0/version > /dev/null
if [ $? -ne 0 ]; then
    echo "IPFS is not running. Please start the IPFS daemon first."
    echo "You can start it with: docker-compose up -d ipfs"
    exit 1
fi

# Create test directories if they don't exist
echo "Creating test directories..."
mkdir -p local_storage/records
mkdir -p local_storage/purchases
mkdir -p local_storage/transactions
mkdir -p secure_data

# Run a simple import test first
echo "Running import test..."
python -c "
print('Importing constants...')
from backend.constants import ROLES, PATIENT_ADDRESS, DOCTOR_ADDRESS

print('Importing auth_utils...')
from backend.auth_utils import generate_auth_challenge, verify_auth_signature, is_authenticated, get_role

print('Importing api...')
import backend.api

print('All imports successful!')
"

# Run the tests
echo "Running authentication tests..."
python tests/test_auth.py

echo "Running group signature tests..."
python tests/test_groupsig.py

echo "Running API tests..."
python tests/test_api.py

echo "Running feature tests..."
python tests/test_features.py

# Check the test result
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed. Please check the output above for details."
fi

echo "Test run completed."
