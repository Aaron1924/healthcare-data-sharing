#!/bin/bash
# Script to optimize network settings for Docker containers

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
  print_warning "This script should be run as root to modify system settings."
  print_warning "Running with limited functionality."
  AS_ROOT=false
else
  AS_ROOT=true
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker first."
  exit 1
fi

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

# Check if ports are open
print_message "Checking if ports are open..."

check_port() {
  local port=$1
  local service=$2
  
  if command -v nc &> /dev/null; then
    if nc -z localhost $port; then
      print_message "Port $port ($service) is open locally."
    else
      print_warning "Port $port ($service) is not open locally."
    fi
  else
    print_warning "netcat not available, skipping port check."
  fi
}

check_port 8501 "Streamlit UI"
check_port 8000 "API"
check_port 8080 "File Server"

# Optimize system network settings if running as root
if [ "$AS_ROOT" = true ]; then
  print_message "Optimizing system network settings..."
  
  # Increase the maximum number of open files
  sysctl -w fs.file-max=100000
  
  # Increase the local port range
  sysctl -w net.ipv4.ip_local_port_range="1024 65535"
  
  # Increase TCP max buffer size
  sysctl -w net.core.rmem_max=16777216
  sysctl -w net.core.wmem_max=16777216
  
  # Increase TCP autotuning buffer limits
  sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
  sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
  
  # Enable TCP fast open
  sysctl -w net.ipv4.tcp_fastopen=3
  
  # Increase the maximum backlog
  sysctl -w net.core.somaxconn=65535
  
  print_message "System network settings optimized."
else
  print_warning "Skipping system network optimization (requires root)."
fi

# Restart Docker containers with optimized settings
print_message "Restarting Docker containers with optimized settings..."

# Stop containers
docker-compose -f docker-compose-simple.yml down

# Start containers with optimized settings
docker-compose -f docker-compose-simple.yml up -d

# Wait for containers to start
print_message "Waiting for containers to start..."
sleep 10

# Check container status
print_message "Container status:"
docker ps

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

print_message "Network optimization complete!"
print_message "If external access is still slow, consider the following:"
print_message "1. Check your firewall settings"
print_message "2. Verify your router configuration"
print_message "3. Try accessing from a different device on the same network"
print_message "4. Consider using a reverse proxy like Nginx for better performance"
