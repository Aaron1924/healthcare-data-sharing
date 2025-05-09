#!/bin/bash
# Script to initialize IPFS with proper configuration

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

# Create IPFS data directory if it doesn't exist
if [ ! -d "ipfs-data" ]; then
  print_message "Creating IPFS data directory..."
  mkdir -p ipfs-data
  chmod 777 ipfs-data
fi

# Create local storage directory if it doesn't exist
if [ ! -d "local_storage" ]; then
  print_message "Creating local storage directory..."
  mkdir -p local_storage
  chmod 777 local_storage
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker first."
  exit 1
fi

# Check if the IPFS container is running
if docker ps | grep -q ipfs-node; then
  print_message "IPFS container is already running. Stopping it first..."
  docker stop ipfs-node
  docker rm ipfs-node
fi

# Start the IPFS container in initialization mode
print_message "Starting IPFS container in initialization mode..."
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 init

# Configure IPFS
print_message "Configuring IPFS..."
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json API.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json API.HTTPHeaders.Access-Control-Allow-Methods '["PUT", "POST", "GET"]'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json Addresses.API '"/ip4/0.0.0.0/tcp/5001"'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json Addresses.Gateway '"/ip4/0.0.0.0/tcp/8080"'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config Datastore.StorageMax "10GB"

print_message "IPFS initialization complete!"
print_message "You can now start the containers with: ./docker-setup.sh start"
