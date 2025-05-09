#!/bin/bash
# Script to properly stop all Docker containers and remove networks

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

# List all running containers
print_message "Checking for running containers..."
RUNNING_CONTAINERS=$(docker ps -q)

if [ -n "$RUNNING_CONTAINERS" ]; then
  print_message "Found running containers. Stopping them..."
  
  # Stop all running containers
  docker stop $(docker ps -q)
  
  if [ $? -eq 0 ]; then
    print_message "All containers stopped successfully."
  else
    print_error "Failed to stop some containers."
    exit 1
  fi
else
  print_message "No running containers found."
fi

# List all containers (including stopped ones)
print_message "Checking for all containers (including stopped ones)..."
ALL_CONTAINERS=$(docker ps -a -q)

if [ -n "$ALL_CONTAINERS" ]; then
  print_message "Found containers. Removing them..."
  
  # Remove all containers
  docker rm -f $(docker ps -a -q)
  
  if [ $? -eq 0 ]; then
    print_message "All containers removed successfully."
  else
    print_error "Failed to remove some containers."
    exit 1
  fi
else
  print_message "No containers found."
fi

# List all networks
print_message "Checking for custom networks..."
CUSTOM_NETWORKS=$(docker network ls --filter "name=pygroupsig" -q)

if [ -n "$CUSTOM_NETWORKS" ]; then
  print_message "Found custom networks. Removing them..."
  
  # Remove each network individually
  for NETWORK in $(docker network ls --filter "name=pygroupsig" --format "{{.Name}}"); do
    print_message "Removing network: $NETWORK"
    docker network rm $NETWORK
    
    if [ $? -eq 0 ]; then
      print_message "Network $NETWORK removed successfully."
    else
      print_warning "Failed to remove network $NETWORK. It might still have endpoints."
      
      # Try to find containers connected to this network
      print_message "Checking for containers connected to network $NETWORK..."
      CONNECTED_CONTAINERS=$(docker network inspect $NETWORK -f '{{range .Containers}}{{.Name}} {{end}}')
      
      if [ -n "$CONNECTED_CONTAINERS" ]; then
        print_warning "Found containers connected to network $NETWORK: $CONNECTED_CONTAINERS"
        print_message "Disconnecting containers from network..."
        
        for CONTAINER in $CONNECTED_CONTAINERS; do
          print_message "Disconnecting container $CONTAINER from network $NETWORK..."
          docker network disconnect -f $NETWORK $CONTAINER
          
          if [ $? -eq 0 ]; then
            print_message "Container $CONTAINER disconnected from network $NETWORK."
          else
            print_error "Failed to disconnect container $CONTAINER from network $NETWORK."
          fi
        done
        
        # Try to remove the network again
        print_message "Trying to remove network $NETWORK again..."
        docker network rm $NETWORK
        
        if [ $? -eq 0 ]; then
          print_message "Network $NETWORK removed successfully."
        else
          print_error "Failed to remove network $NETWORK. Manual intervention required."
        fi
      else
        print_message "No containers found connected to network $NETWORK."
      fi
    fi
  done
else
  print_message "No custom networks found."
fi

print_message "Cleanup complete!"
print_message "You can now start the containers again with a clean state."
