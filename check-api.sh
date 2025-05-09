#!/bin/bash
# Script to check if the API is working properly

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker first."
  exit 1
fi

# Check if the API container exists
if ! docker ps -a | grep -q healthcare-api; then
  print_error "API container not found. Please start the containers first."
  exit 1
fi

# Check if the API container is running
if ! docker ps | grep -q healthcare-api; then
  print_warning "API container exists but is not running. Starting it..."
  docker start healthcare-api
  sleep 5
fi

# Get the API container logs
print_message "API container logs:"
docker logs healthcare-api

# Check if the API is responding
print_message "Checking if the API is responding..."
if docker exec healthcare-api curl -s http://localhost:8000/ > /dev/null; then
  print_message "API is responding!"
else
  print_warning "API is not responding. Checking for errors..."
  
  # Check for common issues
  print_message "Checking for MCL library issues..."
  docker exec healthcare-api ls -la /usr/local/lib/mcl || true
  
  print_message "Checking Python dependencies..."
  docker exec healthcare-api pip list | grep -E 'fastapi|uvicorn|web3|ipfs'
  
  print_message "Checking environment variables..."
  docker exec healthcare-api env | grep -E 'IPFS|MCL|PYTHONPATH'
  
  print_message "Trying to start the API manually..."
  docker exec -d healthcare-api bash -c "cd /app && uvicorn backend.api:app --host 0.0.0.0 --port 8000"
  
  print_message "Waiting for API to start..."
  sleep 10
  
  if docker exec healthcare-api curl -s http://localhost:8000/ > /dev/null; then
    print_message "API is now responding!"
  else
    print_error "API is still not responding. Please check the logs for more details."
  fi
fi

# Check if the web container is running
if docker ps | grep -q healthcare-web; then
  print_message "Web container is running."
else
  print_warning "Web container is not running. Starting it..."
  docker start healthcare-web
fi

print_message "Check complete!"
