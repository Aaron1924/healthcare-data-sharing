#!/bin/bash
# Script to test contract interaction from inside the Docker container

set -e  # Exit on error

echo "=== Testing Contract Interaction in Docker ==="

# Make sure the container is running
if ! docker-compose ps | grep -q "api.*Up"; then
    echo "❌ API container is not running. Starting containers..."
    docker-compose up -d
    sleep 5  # Wait for containers to start
fi

# Copy the test script into the container
echo "📋 Copying test script into the container..."
docker cp test_contract.py $(docker-compose ps -q api):/app/

# Run the test script inside the container
echo "⏳ Running contract test inside Docker container..."
docker-compose exec api python /app/test_contract.py

echo "=== Test Complete ==="
