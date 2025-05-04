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

## Testing

### Testing Smart Contract Interaction

To test that your smart contract can interact with the Base Sepolia blockchain:

```bash
# Make the test script executable
chmod +x run_contract_test.sh

# Run the test
./run_contract_test.sh
```

This will:
1. Ensure the Docker containers are running
2. Copy the test script into the container
3. Execute the contract test script inside the API container
4. Test read operations, write operations, and event listening

The test script will:
- Connect to the Base Sepolia testnet
- Load your contract ABI from the artifacts directory
- Test reading from the contract (groupManager, revocationManager, seq)
- Test writing to the contract (request or storeData)
- Test listening for events (DataStored or RequestOpen)

Alternatively, you can run the test directly in the container:

```bash
# Copy the test script to the container
docker cp test_contract.py $(docker-compose ps -q api):/app/

# Run the test script directly in the container
docker-compose exec api python /app/test_contract.py
```

#### Important Note for WSL Users

When running in WSL with Docker, the paths to the contract artifacts need to be correctly mapped:

- Windows path: `C:\Users\pkhoa\OneDrive - VNU-HCMUS\Documents\SCHOOL\Khoá luận\main\healthcare-data-sharing\artifacts`
- WSL path: `/mnt/c/Users/pkhoa/OneDrive - VNU-HCMUS/Documents/SCHOOL/Khoá luận/main/healthcare-data-sharing/artifacts`
- Docker container path: `/app/artifacts` (as mounted in docker-compose.yml)

#### Base Sepolia Blockchain Limitations

When testing with the Base Sepolia testnet, be aware of these limitations:

- **Event Query Limit**: Base Sepolia limits event queries to at most 1000 blocks. The test script handles this by limiting queries to 500 blocks.
- **Gas Costs**: Some functions (like `request()`) require sending ETH along with the transaction. The test script will fall back to using `storeData()` if there are insufficient funds.
- **Rate Limiting**: Public RPC endpoints may have rate limiting. If you encounter issues, consider using a dedicated RPC provider.

### Testing MCL and Group Signatures

The MCL library is required for the group signature functionality. The Docker container is configured to build and install the MCL library automatically.

#### MCL Library Dependencies

The MCL library requires the following dependencies:
- libgmp-dev
- libgmp10
- libgmpxx4ldbl

These are installed automatically in the Docker container.

#### Group Signature Keys

The group signature keys are generated automatically when the Docker container is built. The keys are stored in the `/app/keys` directory inside the container.

To verify that the MCL library and pygroupsig are working correctly:

```bash
# Make the test script executable
chmod +x test_mcl_in_container.sh

# Run the test script
./test_mcl_in_container.sh
```

This will:
1. Ensure the Docker containers are running
2. Run the MCL test script inside the container
3. Run the group signature test script inside the container

Alternatively, you can run the tests directly:

```bash
# Test MCL library
docker-compose exec api python /app/test_mcl.py

# Test group signatures
docker-compose exec api python /app/test.py
```

## Troubleshooting

### MCL Library and Group Signatures

If you encounter issues with the MCL library or group signatures:

1. **Check MCL_LIB_PATH**: Make sure the MCL_LIB_PATH environment variable is set correctly in the container:
   ```bash
   docker-compose exec api env | grep MCL_LIB_PATH
   ```
   It should be set to `/usr/local/lib/mcl`.

2. **Check MCL library files**: Verify that the MCL library files exist in the container:
   ```bash
   docker-compose exec api ls -la /usr/local/lib/mcl
   ```
   You should see `libmcl.so` and `libmclbn384_256.so`.

3. **Rebuild the container**: If the MCL library is missing or not working, try rebuilding the container:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Generate keys manually**: If the group signature keys are missing, you can generate them manually:
   ```bash
   docker-compose exec api python /app/generate_keys.py
   ```

5. **Check for GMP dependencies**: The MCL library requires GMP dependencies. Make sure they are installed:
   ```bash
   docker-compose exec api apt-get update && apt-get install -y libgmp-dev libgmp10 libgmpxx4ldbl
   ```

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
```

### Smart Contract Issues

If you encounter issues with smart contract interaction:

```bash
# Check if you have ETH in your account
docker-compose exec api python -c "from web3 import Web3; from dotenv import load_dotenv; import os; load_dotenv(); w3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL'))); print(f'Balance: {w3.from_wei(w3.eth.get_balance(os.getenv(\"WALLET_ADDRESS\")), \"ether\")} ETH')"

# Get testnet ETH from the Base Sepolia faucet
echo "Visit https://faucet.base.org/ to get testnet ETH"
```

## License

[MIT License](LICENSE)