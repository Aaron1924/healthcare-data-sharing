# Healthcare Data Sharing Platform

A blockchain-based platform for secure healthcare data sharing using group signatures and IPFS.

## Features

- Secure storage of healthcare records using IPFS and encryption
- Group signature-based authentication and privacy
- Smart contract integration for access control and data sharing
- Web-based interface for patients, doctors, and healthcare providers

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

## Running the Project with Docker

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/healthcare-data-sharing.git
cd healthcare-data-sharing
```

### 2. Configure Environment Variables (Optional)

The project includes default environment variables in the `.env` file. You can modify these if needed:

```bash
# Edit the .env file if you need to change any settings
nano .env
```

### 3. Build and Start the Docker Containers

```bash
# Build the Docker images
docker-compose build

# Start the containers
docker-compose up
```

Alternatively, you can run the containers in detached mode:

```bash
docker-compose up -d
```

### 4. Access the Application

- **Web UI**: [http://localhost:8501](http://localhost:8501)
- **API**: [http://localhost:8000](http://localhost:8000)
- **IPFS Interface**: [http://localhost:8080/webui](http://localhost:8080/webui)

### 5. Stop the Containers

To stop the running containers:

```bash
# If running in the foreground, press Ctrl+C
# If running in detached mode:
docker-compose down
```

## Project Structure

- `app/`: Streamlit web application
- `backend/`: FastAPI backend services
- `pygroupsig/`: Python implementation of group signatures
- `artifacts/`: Smart contract artifacts
- `Dockerfile`: Docker configuration for the application
- `docker-compose.yml`: Docker Compose configuration

## Technical Details

### MCL Library

The project uses the [MCL library](https://github.com/herumi/mcl) for pairing-based cryptography, which is required by the pygroupsig library. The Docker setup automatically:

1. Installs the required dependencies (including libgmp-dev)
2. Clones and builds the MCL library
3. Sets up the necessary environment variables

### Group Signatures

The project uses a Python implementation of group signatures (pygroupsig) for privacy-preserving authentication. This allows:

- Patients to sign data without revealing their identity
- Verification of signatures without identifying the signer
- Revocation of anonymity when necessary (by authorized entities)

### IPFS Storage

Healthcare data is stored on IPFS (InterPlanetary File System), providing:

- Decentralized storage
- Content-addressed data (immutable references)
- Resilient data availability

## Troubleshooting

### Docker Permission Issues

If you encounter permission issues with Docker:

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER
newgrp docker
```

### MCL Library Issues

If you encounter issues with the MCL library:

```bash
# Check if the MCL library is properly built
docker-compose exec api ls -la /usr/local/lib/mcl

# Test the MCL library and pygroupsig
docker-compose exec api python /app/test_mcl.py
```

## License

[MIT License](LICENSE)