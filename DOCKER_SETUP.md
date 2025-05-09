# Docker Setup for Healthcare Data Sharing

This document provides instructions for setting up and running the Healthcare Data Sharing application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

We've provided a convenient script to help you set up and manage the Docker environment:

```bash
# Make the script executable (if not already)
chmod +x docker-setup.sh

# Start the containers
./docker-setup.sh start

# Create sample data (after containers are running)
./docker-setup.sh samples
```

Once the containers are running, you can access:
- Web UI: http://localhost:8501
- API: http://localhost:8000
- IPFS Gateway: http://localhost:8080
- IPFS WebUI: http://localhost:5001/webui

## Manual Setup

If you prefer to set up manually:

1. Create necessary directories:
```bash
mkdir -p local_storage/records
mkdir -p local_storage/purchases
mkdir -p local_storage/transactions
mkdir -p local_storage/store_transactions
mkdir -p local_storage/share_transactions
mkdir -p local_storage/purchase_transactions
mkdir -p keys
```

2. Create a `.env` file with your configuration (see `.env.example` for reference)

3. Build and start the containers:
```bash
docker-compose up --build -d
```

## Components

The Docker setup includes the following components:

1. **Web UI (Streamlit)**
   - Container: `healthcare-web`
   - Port: 8501
   - Provides the user interface for interacting with the system

2. **API (FastAPI)**
   - Container: `healthcare-api`
   - Port: 8000
   - Handles backend logic and blockchain interactions

3. **IPFS Node**
   - Container: `ipfs-node`
   - Ports: 4001 (swarm), 5001 (API), 8080 (gateway)
   - Stores and retrieves data in a decentralized manner

## Troubleshooting

### IPFS Connection Issues

If the API can't connect to IPFS, try:

```bash
# Restart the IPFS container
docker-compose restart ipfs

# Wait a moment, then restart the API
docker-compose restart api
```

### MCL Library Issues

If you encounter issues with the MCL library:

```bash
# Rebuild the containers
docker-compose down
docker-compose up --build -d
```

### Viewing Logs

To view logs for troubleshooting:

```bash
# View logs for all containers
./docker-setup.sh logs

# Or manually for specific containers
docker-compose logs -f web
docker-compose logs -f api
docker-compose logs -f ipfs
```

## Cleaning Up

To stop and remove all containers:

```bash
./docker-setup.sh stop
```

To completely clean up (including volumes and local data):

```bash
./docker-setup.sh cleanup
```

## Advanced Configuration

### Customizing Environment Variables

Edit the `.env` file to customize:
- RPC URLs
- Contract addresses
- Private keys
- API keys

### Persistent Storage

The following volumes are used for persistent storage:
- `ipfs-data`: IPFS data
- Local directories mounted into containers:
  - `./local_storage`: Application data
  - `./keys`: Group signature keys
  - `./artifacts`: Smart contract artifacts

## Security Considerations

**Warning**: The default private keys included in this setup are for development purposes only. Never use these keys in a production environment.

For production:
1. Generate new private keys
2. Use secure storage for keys
3. Consider using a secrets management solution
4. Implement proper access controls for the API and IPFS node
