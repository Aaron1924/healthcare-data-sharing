#!/bin/bash
# Script to run the simple version without IPFS

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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  print_error "Docker is not installed or not in PATH. Please install Docker first."
  print_error "If you're using WSL, make sure Docker Desktop is running and WSL integration is enabled."
  exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  print_error "Docker Compose is not installed or not in PATH. Please install Docker Compose first."
  exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
  print_error "Docker daemon is not running. Please start Docker service first."
  exit 1
fi

# Create necessary directories
print_message "Creating necessary directories..."
mkdir -p local_storage/records
mkdir -p local_storage/purchases
mkdir -p local_storage/transactions
mkdir -p local_storage/store_transactions
mkdir -p local_storage/share_transactions
mkdir -p local_storage/purchase_transactions
mkdir -p keys

# Check if .env file exists, create if not
if [ ! -f .env ]; then
  print_message "Creating .env file with default values..."
  cat > .env << EOL
# Ethereum Sepolia testnet connection
SEPOLIA_RPC_URL=https://ethereum-sepolia.publicnode.com
CONTRACT_ADDRESS=0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA

# Account private keys (DO NOT USE THESE IN PRODUCTION)
PRIVATE_KEY=91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e
DOCTOR_PRIVATE_KEY=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
PATIENT_PRIVATE_KEY=59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
HOSPITAL_PRIVATE_KEY=5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
GROUP_MANAGER_PRIVATE_KEY=7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6
REVOCATION_MANAGER_PRIVATE_KEY=47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a
BUYER_PRIVATE_KEY=8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba

# API Keys
ETHERSCAN_API_KEY=TZEJMZ7FRUEI3H4YP5VYEFCU3UZ6SZE8J7
EOL
  print_message ".env file created successfully."
else
  print_message ".env file already exists, skipping creation."
fi

# Start the containers using the simple version
print_message "Building and starting containers with simple configuration (no IPFS)..."
docker-compose -f docker-compose-simple.yml up --build -d

if [ $? -eq 0 ]; then
  print_message "Containers started successfully!"
  
  # Get the local IP address for external access
  if command -v ip &> /dev/null; then
    # Linux
    LOCAL_IP=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1)
  elif command -v ipconfig &> /dev/null; then
    # Windows
    LOCAL_IP=$(ipconfig | grep -oP '(?<=IPv4 Address[.\s]*: )\d+(\.\d+){3}' | head -n 1)
  else
    LOCAL_IP="your-server-ip"
  fi
  
  print_message "Local access:"
  print_message "  Web UI: http://localhost:8501"
  print_message "  API: http://localhost:8000"
  print_message "  File Server: http://localhost:8080"
  
  print_message ""
  print_message "External access (share these URLs with others):"
  print_message "  Web UI: http://$LOCAL_IP:8501"
  print_message "  API: http://$LOCAL_IP:8000"
  print_message "  File Server: http://$LOCAL_IP:8080"
  print_message ""
  print_message "Note: This is running with a simple file server instead of IPFS."
else
  print_error "Failed to start containers. Check the logs for more information."
  exit 1
fi
