#!/bin/bash
# Script to configure Docker daemon to listen on TCP port 2375

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

# Determine the OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$ID
else
  OS=$(uname -s)
fi

print_message "Detected OS: $OS"

# Create Docker daemon.json file
print_message "Creating Docker daemon configuration..."

DOCKER_CONFIG_DIR="/etc/docker"
DOCKER_CONFIG_FILE="$DOCKER_CONFIG_DIR/daemon.json"

# Create directory if it doesn't exist
mkdir -p $DOCKER_CONFIG_DIR

# Check if daemon.json already exists
if [ -f "$DOCKER_CONFIG_FILE" ]; then
  print_message "Existing daemon.json found. Creating backup..."
  cp "$DOCKER_CONFIG_FILE" "$DOCKER_CONFIG_FILE.bak"
  
  # Check if hosts key already exists in the file
  if grep -q '"hosts"' "$DOCKER_CONFIG_FILE"; then
    print_warning "hosts configuration already exists in daemon.json."
    print_warning "Modifying existing configuration..."
    
    # Use temporary file for editing
    TMP_FILE=$(mktemp)
    
    # Extract current content as JSON, modify hosts, and write back
    cat "$DOCKER_CONFIG_FILE" | \
      python3 -c "
import json, sys
config = json.load(sys.stdin)
config['hosts'] = ['unix:///var/run/docker.sock', 'tcp://0.0.0.0:2375']
json.dump(config, sys.stdout, indent=2)
" > "$TMP_FILE"
    
    # Check if the operation was successful
    if [ $? -eq 0 ]; then
      mv "$TMP_FILE" "$DOCKER_CONFIG_FILE"
    else
      print_error "Failed to modify daemon.json. Using direct approach..."
      echo '{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}' > "$DOCKER_CONFIG_FILE"
    fi
  else
    # Hosts key doesn't exist, merge with existing config
    TMP_FILE=$(mktemp)
    
    # Extract current content as JSON, add hosts, and write back
    cat "$DOCKER_CONFIG_FILE" | \
      python3 -c "
import json, sys
config = json.load(sys.stdin)
config['hosts'] = ['unix:///var/run/docker.sock', 'tcp://0.0.0.0:2375']
json.dump(config, sys.stdout, indent=2)
" > "$TMP_FILE"
    
    # Check if the operation was successful
    if [ $? -eq 0 ]; then
      mv "$TMP_FILE" "$DOCKER_CONFIG_FILE"
    else
      print_error "Failed to modify daemon.json. Using direct approach..."
      echo '{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}' > "$DOCKER_CONFIG_FILE"
    fi
  fi
else
  # Create new daemon.json file
  echo '{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}' > "$DOCKER_CONFIG_FILE"
fi

print_message "Docker daemon configuration created at $DOCKER_CONFIG_FILE"

# Update systemd configuration if needed
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ] || [ "$OS" = "centos" ] || [ "$OS" = "fedora" ]; then
  print_message "Updating systemd configuration..."
  
  SYSTEMD_DIR="/etc/systemd/system/docker.service.d"
  mkdir -p "$SYSTEMD_DIR"
  
  echo '[Service]
ExecStart=
ExecStart=/usr/bin/dockerd' > "$SYSTEMD_DIR/override.conf"
  
  print_message "Reloading systemd configuration..."
  systemctl daemon-reload
fi

# Restart Docker service
print_message "Restarting Docker service..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ] || [ "$OS" = "centos" ] || [ "$OS" = "fedora" ]; then
  systemctl restart docker
elif [ "$OS" = "alpine" ]; then
  rc-service docker restart
else
  service docker restart
fi

# Check if Docker service is running
sleep 2
if systemctl is-active --quiet docker || service docker status > /dev/null 2>&1; then
  print_message "Docker service restarted successfully."
else
  print_error "Failed to restart Docker service. Please check the logs."
  exit 1
fi

# Configure firewall if needed
print_message "Checking firewall configuration..."
if command -v ufw > /dev/null 2>&1; then
  print_message "UFW firewall detected. Opening port 2375..."
  ufw allow 2375/tcp
elif command -v firewall-cmd > /dev/null 2>&1; then
  print_message "FirewallD detected. Opening port 2375..."
  firewall-cmd --permanent --add-port=2375/tcp
  firewall-cmd --reload
else
  print_warning "No supported firewall detected. Please manually ensure port 2375 is open."
fi

# Get server IP address
if command -v ip &> /dev/null; then
  SERVER_IP=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1)
elif command -v ifconfig &> /dev/null; then
  SERVER_IP=$(ifconfig | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1)
else
  SERVER_IP="<your-server-ip>"
fi

print_message "Configuration complete!"
print_message "Docker daemon is now listening on:"
print_message "  - Unix socket: unix:///var/run/docker.sock"
print_message "  - TCP: tcp://$SERVER_IP:2375"
print_message ""
print_warning "SECURITY WARNING: The Docker daemon is now accessible over the network without TLS encryption."
print_warning "This configuration should only be used in a secure environment."
print_warning "For production environments, configure TLS certificates and use port 2376 instead."
print_message ""
print_message "To connect to this Docker daemon from another machine, use:"
print_message "  docker -H tcp://$SERVER_IP:2375 info"
print_message ""
print_message "To set the DOCKER_HOST environment variable:"
print_message "  export DOCKER_HOST=tcp://$SERVER_IP:2375"
