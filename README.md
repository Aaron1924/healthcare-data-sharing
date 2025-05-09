# Decentralized Healthcare Data Sharing Platform

A blockchain-based platform for secure healthcare data sharing using group signatures and IPFS, deployed on the Ethereum Sepolia testnet.

## Features

- **Secure Storage**: Healthcare records are encrypted and stored on IPFS
- **Privacy-Preserving Authentication**: Group signatures ensure doctor anonymity while maintaining verifiability
- **Blockchain Integration**: Smart contracts on Ethereum Sepolia testnet for access control and data sharing
- **Three Core Workflows**:
  - **Storing**: Doctors create and sign records, patients store them
  - **Sharing**: Patients share records with specific doctors
  - **Purchasing**: Buyers request data that hospitals and patients fulfill

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)
- [Ethereum Sepolia Testnet ETH](https://sepoliafaucet.com/) (for blockchain transactions)

## Running the Project with Docker

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/healthcare-data-sharing.git
cd healthcare-data-sharing
```

### 2. Configure Environment Variables

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
# Edit the .env file with your preferred editor
nano .env
```

Important variables to configure:
- `SEPOLIA_RPC_URL`: Your Ethereum Sepolia RPC URL (get from Infura, Alchemy, or other providers)
- `PRIVATE_KEY`: Your wallet's private key for contract deployment
- Test account private keys (if you want to use different accounts)

### 3. Build and Start the Docker Containers

```bash
# Build and start all containers (web UI, API backend, and IPFS)
docker-compose up --build
```

For production or background running:

```bash
docker-compose up -d
```

### 4. Access the Application

#### Local Access

- **Web UI**: [http://localhost:8501](http://localhost:8501)
- **API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **IPFS Interface**: [http://localhost:5001/webui](http://localhost:5001/webui)

#### External Access

The application is configured to be accessible from other machines on your network. See [EXTERNAL_ACCESS.md](EXTERNAL_ACCESS.md) for detailed instructions on how to:

- Configure your firewall
- Find your server's IP address
- Share access with others
- Set up security measures

### 5. Stop the Containers

```bash
# If running in the foreground, press Ctrl+C
# If running in detached mode:
docker-compose down
```

### 6. Running Individual Components

If you need to run only specific components:

```bash
# Run only the IPFS node
docker-compose up ipfs

# Run only the backend API
docker-compose up api

# Run only the web UI
docker-compose up web
```

## Project Structure

- `app/`: Streamlit web application for the user interface
- `backend/`: FastAPI backend services for API endpoints and business logic
- `pygroupsig/`: Python implementation of group signatures for privacy-preserving authentication
- `artifacts/`: Smart contract artifacts (ABI and bytecode)
- `contracts/`: Solidity smart contracts for the BASE blockchain
- `local_storage/`: Local storage for IPFS data and purchase requests
- `keys/`: Group signature keys for the system
- `Dockerfile`: Docker configuration for building the application
- `docker-compose.yml`: Docker Compose configuration for running all components

## Technical Details

### System Architecture

The system consists of three main components:

1. **Streamlit Web UI**: User interface for patients, doctors, hospitals, and buyers
2. **FastAPI Backend**: API endpoints for data processing, cryptography, and blockchain interaction
3. **IPFS Node**: Decentralized storage for healthcare records and metadata

All components are containerized using Docker and can be run together using Docker Compose.

### MCL Library

The project uses the [MCL library](https://github.com/herumi/mcl) for pairing-based cryptography, which is required by the pygroupsig library. The Docker setup automatically:

1. Installs the required dependencies (including libgmp-dev)
2. Clones and builds the MCL library
3. Sets up the necessary environment variables

### Group Signatures

The project uses a Python implementation of group signatures (pygroupsig) for privacy-preserving authentication. This allows:

- Doctors to sign records without revealing their identity
- Verification of signatures without identifying the signer
- Revocation of anonymity when necessary (by authorized entities)

### IPFS Storage

Healthcare data is stored on IPFS (InterPlanetary File System), providing:

- Decentralized storage
- Content-addressed data (immutable references)
- Resilient data availability
- Encryption for privacy

### Smart Contracts

The project uses Solidity smart contracts deployed on the BASE Sepolia testnet:

- `DataHub.sol`: Main contract for storing, sharing, and purchasing healthcare data
- Functions include: `storeData()`, `request()`, `reply()`, and `finalize()`

## Testing

### Testing Smart Contract Interaction

To test that your smart contract can interact with the Ethereum Sepolia blockchain:

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
- Connect to the Ethereum Sepolia testnet
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

#### Ethereum Sepolia Blockchain Limitations

When testing with the Ethereum Sepolia testnet, be aware of these limitations:

- **Event Query Limit**: Ethereum Sepolia limits event queries to at most 1000 blocks. The test script handles this by limiting queries to 500 blocks.
- **Gas Costs**: Some functions (like `request()`) require sending ETH along with the transaction. The test script will fall back to using `storeData()` if there are insufficient funds.
- **Rate Limiting**: Public RPC endpoints may have rate limiting. If you encounter issues, consider using a dedicated RPC provider like Infura or Alchemy.

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

### IPFS Connection Issues

If you encounter issues with IPFS connectivity:

1. **Check if IPFS container is running**:

```bash
docker ps | grep ipfs
```

2. **Check IPFS logs**:

```bash
docker logs ipfs-node
```

3. **Verify IPFS API is accessible**:

```bash
curl -X POST "http://localhost:5001/api/v0/id"
```

4. **Reset IPFS container and data**:

```bash
docker-compose down
rm -rf ipfs-data
mkdir -p ipfs-data
chmod 777 ipfs-data
docker-compose up -d ipfs
```

### MCL Library and Group Signatures

If you encounter issues with the MCL library or group signatures:

1. **Check MCL_LIB_PATH environment variable**:

```bash
docker-compose exec api env | grep MCL_LIB_PATH
```

2. **Verify MCL library files exist**:

```bash
docker-compose exec api ls -la /usr/local/lib/mcl
```

3. **Rebuild the container without cache**:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

4. **Generate group signature keys manually**:

```bash
docker-compose exec api python /app/generate_keys.py
```

### Blockchain Transaction Issues

If you encounter issues with blockchain transactions:

1. **Check wallet balances**:

```bash
# Check the balance of the wallet used for transactions
docker-compose exec api python -c "from web3 import Web3; import os; w3 = Web3(Web3.HTTPProvider(os.getenv('SEPOLIA_RPC_URL'))); print(f'Balance: {w3.from_wei(w3.eth.get_balance(os.getenv(\"WALLET_ADDRESS\")), \"ether\")} ETH')"
```

2. **Get testnet ETH**:
   - Visit [Ethereum Sepolia Faucet](https://sepoliafaucet.com/)
   - Request ETH for your wallet addresses (doctor, patient, buyer, etc.)

3. **Check contract deployment**:

```bash
# Verify the contract exists at the specified address
docker-compose exec api python -c "from web3 import Web3; import os; import json; w3 = Web3(Web3.HTTPProvider(os.getenv('SEPOLIA_RPC_URL'))); addr = os.getenv('CONTRACT_ADDRESS'); print(f'Contract code exists: {w3.eth.get_code(addr).hex() != \"0x\"}')"
```

### Docker Permission Issues

If you encounter permission issues with Docker:

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Common Error Messages

1. **"Insufficient funds for gas * price + value"**:
   - Solution: Get more testnet ETH from the [Ethereum Sepolia Faucet](https://sepoliafaucet.com/)

2. **"Error loading plugins: open /var/ipfs/config: permission denied"**:
   - Solution: Reset the IPFS container and data as described above

3. **"ImportError: libmcl.so: cannot open shared object file"**:
   - Solution: Rebuild the container without cache to properly install the MCL library

## License

[MIT License](LICENSE)