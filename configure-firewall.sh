#!/bin/bash
# Script to configure UFW firewall for Docker

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  print_error "This script must be run as root (sudo)."
  exit 1
fi

# Check if UFW is installed
if ! command -v ufw &> /dev/null; then
  print_message "UFW is not installed. Installing..."
  apt-get update
  apt-get install -y ufw
fi

# Check current UFW status
print_message "Checking current UFW status..."
ufw status

# Ask for confirmation before enabling UFW
print_warning "This script will enable UFW and configure rules for Docker."
print_warning "If you're connected via SSH, this could potentially lock you out if not configured correctly."
read -p "Are you sure you want to continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  print_message "Operation cancelled."
  exit 0
fi

# Reset UFW to default
print_message "Resetting UFW to default..."
ufw --force reset

# Set default policies
print_message "Setting default policies..."
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (to prevent locking yourself out)
print_message "Allowing SSH..."
ufw allow ssh

# Allow Docker ports
print_message "Allowing Docker ports..."
ufw allow 2375/tcp  # Docker API
ufw allow 8501/tcp  # Streamlit UI
ufw allow 8000/tcp  # FastAPI
ufw allow 5001/tcp  # IPFS API
ufw allow 8080/tcp  # IPFS Gateway/File Server
ufw allow 4001/tcp  # IPFS Swarm

# Enable UFW
print_message "Enabling UFW..."
ufw --force enable

# Check UFW status
print_message "UFW status:"
ufw status verbose

print_message "Firewall configuration complete!"
print_message "The following ports are now open:"
print_message "  - 22/tcp (SSH)"
print_message "  - 2375/tcp (Docker API)"
print_message "  - 8501/tcp (Streamlit UI)"
print_message "  - 8000/tcp (FastAPI)"
print_message "  - 5001/tcp (IPFS API)"
print_message "  - 8080/tcp (IPFS Gateway/File Server)"
print_message "  - 4001/tcp (IPFS Swarm)"
print_message ""
print_message "If you need to open additional ports, use:"
print_message "  sudo ufw allow PORT/tcp"
print_message ""
print_message "If you need to disable the firewall, use:"
print_message "  sudo ufw disable"
