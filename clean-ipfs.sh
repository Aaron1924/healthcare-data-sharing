#!/bin/bash
# Script to clean up IPFS data and reinitialize

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

# Stop and remove IPFS container if it's running
if docker ps -a | grep -q ipfs-node; then
  print_message "Stopping and removing IPFS container..."
  docker stop ipfs-node 2>/dev/null || true
  docker rm ipfs-node 2>/dev/null || true
fi

# Ask for confirmation before removing data
print_warning "This will remove all IPFS data and reinitialize the repository."
print_warning "Any data stored in IPFS will be lost."
read -p "Are you sure you want to continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  print_message "Operation cancelled."
  exit 0
fi

# Remove IPFS data directory
print_message "Removing IPFS data directory..."
if [ -d "ipfs-data" ]; then
  rm -rf ipfs-data
  print_message "IPFS data directory removed."
else
  print_message "IPFS data directory not found. Nothing to remove."
fi

# Create IPFS data directory
print_message "Creating new IPFS data directory..."
mkdir -p ipfs-data
chmod 777 ipfs-data

# Initialize IPFS with the latest version
print_message "Initializing IPFS with the latest version..."
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 init

# Configure IPFS
print_message "Configuring IPFS..."
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json API.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json API.HTTPHeaders.Access-Control-Allow-Methods '["PUT", "POST", "GET"]'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json Addresses.API '"/ip4/0.0.0.0/tcp/5001"'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config --json Addresses.Gateway '"/ip4/0.0.0.0/tcp/8080"'
docker run --rm -v "$(pwd)/ipfs-data:/data/ipfs" ipfs/kubo:v0.22.0 config Datastore.StorageMax "10GB"

print_message "IPFS cleanup and initialization complete!"
print_message "You can now start the containers with: ./docker-setup.sh start"
