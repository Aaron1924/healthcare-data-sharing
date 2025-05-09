#!/bin/bash
# Script to verify Docker host configuration

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

# Get server IP address
if command -v ip &> /dev/null; then
  SERVER_IP=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1)
elif command -v ifconfig &> /dev/null; then
  SERVER_IP=$(ifconfig | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1)
else
  SERVER_IP="<your-server-ip>"
fi

print_message "Server IP address: $SERVER_IP"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker first."
  exit 1
fi

# Check Docker daemon configuration
print_message "Checking Docker daemon configuration..."

if [ -f /etc/docker/daemon.json ]; then
  print_message "Docker daemon.json exists:"
  cat /etc/docker/daemon.json
  
  # Check if hosts configuration is present
  if grep -q '"hosts"' /etc/docker/daemon.json; then
    print_message "hosts configuration is present in daemon.json."
    
    # Check if TCP host is configured
    if grep -q "tcp://0.0.0.0:2375" /etc/docker/daemon.json; then
      print_message "TCP host is configured correctly."
    else
      print_warning "TCP host configuration is missing or incorrect."
    fi
  else
    print_warning "hosts configuration is missing in daemon.json."
  fi
else
  print_warning "Docker daemon.json does not exist."
fi

# Check if Docker is listening on TCP port 2375
print_message "Checking if Docker is listening on TCP port 2375..."

if command -v netstat &> /dev/null; then
  if netstat -tuln | grep -q ":2375"; then
    print_message "Docker is listening on port 2375."
  else
    print_warning "Docker is not listening on port 2375."
  fi
elif command -v ss &> /dev/null; then
  if ss -tuln | grep -q ":2375"; then
    print_message "Docker is listening on port 2375."
  else
    print_warning "Docker is not listening on port 2375."
  fi
else
  print_warning "Neither netstat nor ss available, skipping port check."
fi

# Test Docker connection over TCP
print_message "Testing Docker connection over TCP..."

# Save current DOCKER_HOST
OLD_DOCKER_HOST=$DOCKER_HOST

# Set DOCKER_HOST to TCP
export DOCKER_HOST=tcp://localhost:2375

# Try to connect to Docker over TCP
if docker info > /dev/null 2>&1; then
  print_message "Successfully connected to Docker over TCP (localhost)."
else
  print_warning "Failed to connect to Docker over TCP (localhost)."
fi

# Try to connect using the server IP
export DOCKER_HOST=tcp://$SERVER_IP:2375

if docker info > /dev/null 2>&1; then
  print_message "Successfully connected to Docker over TCP ($SERVER_IP)."
else
  print_warning "Failed to connect to Docker over TCP ($SERVER_IP)."
fi

# Restore original DOCKER_HOST
if [ -z "$OLD_DOCKER_HOST" ]; then
  unset DOCKER_HOST
else
  export DOCKER_HOST=$OLD_DOCKER_HOST
fi

# Check firewall status
print_message "Checking firewall status for port 2375..."

if command -v ufw &> /dev/null; then
  if ufw status | grep -q "2375/tcp"; then
    print_message "UFW firewall has port 2375 open."
  else
    print_warning "UFW firewall does not have port 2375 open."
  fi
elif command -v firewall-cmd &> /dev/null; then
  if firewall-cmd --list-ports | grep -q "2375/tcp"; then
    print_message "FirewallD has port 2375 open."
  else
    print_warning "FirewallD does not have port 2375 open."
  fi
else
  print_warning "No supported firewall detected. Please manually check if port 2375 is open."
fi

print_message "Verification complete!"
print_message ""
print_message "To connect to this Docker daemon from another machine, use:"
print_message "  docker -H tcp://$SERVER_IP:2375 info"
print_message ""
print_message "To set the DOCKER_HOST environment variable:"
print_message "  export DOCKER_HOST=tcp://$SERVER_IP:2375"
