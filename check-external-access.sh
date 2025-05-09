#!/bin/bash
# Script to check external access to Docker containers

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
  # Linux
  SERVER_IP=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1)
elif command -v ipconfig &> /dev/null; then
  # Windows
  SERVER_IP=$(ipconfig | grep -oP '(?<=IPv4 Address[.\s]*: )\d+(\.\d+){3}' | head -n 1)
else
  SERVER_IP="unknown"
fi

print_message "Server IP address: $SERVER_IP"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker first."
  exit 1
fi

# Check if containers are running
print_message "Checking if containers are running..."

if docker ps | grep -q healthcare-web; then
  print_message "Web UI container is running."
else
  print_warning "Web UI container is not running."
fi

if docker ps | grep -q healthcare-api; then
  print_message "API container is running."
else
  print_warning "API container is not running."
fi

if docker ps | grep -q fileserver; then
  print_message "File server container is running."
else
  print_warning "File server container is not running."
fi

# Check container port bindings
print_message "Checking container port bindings..."

check_port_binding() {
  local container=$1
  local port=$2
  local binding=$(docker port $container $port 2>/dev/null)
  
  if [ -n "$binding" ]; then
    print_message "$container port $port is bound to $binding"
    if [[ $binding == *"0.0.0.0"* ]]; then
      print_message "Port is bound to all interfaces (good for external access)."
    else
      print_warning "Port is not bound to all interfaces (may not be accessible externally)."
    fi
  else
    print_warning "$container port $port is not bound."
  fi
}

check_port_binding healthcare-web 8501
check_port_binding healthcare-api 8000
check_port_binding fileserver 80

# Check network connectivity
print_message "Checking network connectivity..."

check_connectivity() {
  local url=$1
  local service=$2
  local timeout=5
  
  print_message "Testing connection to $service at $url (timeout: ${timeout}s)..."
  
  if command -v curl &> /dev/null; then
    if curl -s --connect-timeout $timeout $url > /dev/null; then
      print_message "$service is accessible."
    else
      print_warning "$service is not accessible."
    fi
  elif command -v wget &> /dev/null; then
    if wget -q --timeout=$timeout -O /dev/null $url; then
      print_message "$service is accessible."
    else
      print_warning "$service is not accessible."
    fi
  else
    print_warning "Neither curl nor wget available, skipping connectivity check."
  fi
}

check_connectivity "http://localhost:8501" "Web UI (local)"
check_connectivity "http://localhost:8000" "API (local)"
check_connectivity "http://localhost:8080" "File Server (local)"

if [ "$SERVER_IP" != "unknown" ]; then
  check_connectivity "http://$SERVER_IP:8501" "Web UI (external)"
  check_connectivity "http://$SERVER_IP:8000" "API (external)"
  check_connectivity "http://$SERVER_IP:8080" "File Server (external)"
fi

# Print access URLs
print_message "Access URLs:"
print_message "  Local:"
print_message "    Web UI: http://localhost:8501"
print_message "    API: http://localhost:8000"
print_message "    File Server: http://localhost:8080"
print_message "  External:"
print_message "    Web UI: http://$SERVER_IP:8501"
print_message "    API: http://$SERVER_IP:8000"
print_message "    File Server: http://$SERVER_IP:8080"

print_message "External access check complete!"
print_message "If external access is slow, try running ./optimize-network.sh"
