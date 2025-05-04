#!/bin/bash
# Script to test MCL and group signatures in the Docker container

set -e  # Exit on error

echo "=== Testing MCL and Group Signatures in Docker Container ==="

# Check if the container is running
if ! docker-compose ps | grep -q "api.*Up"; then
    echo "❌ API container is not running. Starting containers..."
    docker-compose up -d
    sleep 5  # Wait for containers to start
fi

# Run the MCL test script inside the container
echo "⏳ Running MCL test inside Docker container..."
docker-compose exec api python /app/test_mcl.py

# Run the group signature test script inside the container
echo "⏳ Running group signature test inside Docker container..."
docker-compose exec api python /app/test.py

echo "=== Test Complete ==="
