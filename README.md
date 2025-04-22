# Decentralized Healthcare Data Sharing (BASE Sepolia Testnet)

This project implements a decentralized healthcare data sharing system on the BASE Sepolia testnet, using group signatures from the _**pygroupsig**_ library. The system allows for secure storing, sharing, and purchasing of healthcare data with cryptographic guarantees.

## Overview

This system implements three main workflows:

1. **Storing**: Doctors create and sign medical records, which patients encrypt and store on IPFS.
2. **Sharing**: Patients can securely share their records with specific doctors.
3. **Purchasing**: Data buyers can purchase anonymized healthcare data with verification.
4. **Revocation Management**: A dual-control mechanism for opening group signatures in case of disputes, requiring approval from both Group Manager and Revocation Manager.

## Architecture

The system consists of three main components:

1. **Streamlit UI**: Web interface for patients, doctors, hospitals, and buyers.
2. **FastAPI Backend**: Handles API requests, cryptographic operations, and blockchain interactions.
3. **IPFS Storage**: Stores encrypted healthcare records.
4. **Smart Contract**: Manages record metadata and purchase escrow on the BASE Sepolia testnet.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- BASE Sepolia testnet wallet with test ETH (get from [BASE Sepolia Faucet](https://www.coinbase.com/faucets/base-sepolia-faucet))
- Python 3.9 or later (if running without Docker)
- MCL library (for group signatures, see [MCL Setup](#mcl-setup) section below)

### Installation

1. Clone this repository
2. Set up environment variables in `.env` file:

   ```bash
  copy .env.example la duoc roi
   ```

3. Run the application using one of the following methods:

#### Using Docker (recommended)

```bash
# Start all services
docker-compose up
```

#### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start IPFS daemon
docker run -d --name ipfs-node -v ipfs-data:/data/ipfs -p 4001:4001 -p 8080:8080 -p 5001:5001 ipfs/kubo

# Start the backend server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# In a new terminal, start the frontend
streamlit run app/main.py
```

After running the above commands, access the UI at [http://localhost:8501](http://localhost:8501)

## Smart Contract

### Deployed Contract

The DataHub contract has already been deployed to the BASE Sepolia testnet with the following details:

- **Contract Address**: [0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6](https://sepolia.basescan.org/address/0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6)
- **Group Manager**: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
- **Revocation Manager**: 0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46

New contributors do NOT need to deploy the contract again. Simply use this address in your `.env` file:

```env
CONTRACT_ADDRESS=0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6
```




## MCL Setup

The pygroupsig library requires the MCL library for cryptographic operations. You can check if MCL is properly set up by running:

```bash
python check_mcl.py
```

If MCL is not set up, the script will guide you through the setup process. Alternatively, you can set it up manually:

1. Clone the MCL repository:
   ```bash
   git clone https://github.com/herumi/mcl.git
   ```

2. Build MCL:
   ```bash
   cd mcl
   cmake -B build .
   make -C build
   ```

3. Set the MCL_LIB_PATH environment variable:
   ```bash
   export MCL_LIB_PATH=$PWD/mcl/build/lib
   ```

4. Add the environment variable to your shell profile (.bashrc, .zshrc, etc.) to make it permanent:
   ```bash
   echo 'export MCL_LIB_PATH=/path/to/mcl/build/lib' >> ~/.bashrc
   source ~/.bashrc
   ```

## IPFS Setup( tao lam docker, xai ipfs desktop thi tu xu nha)

The application uses IPFS for storing encrypted medical records. You can run IPFS in a Docker container:

```bash
# Pull the IPFS Docker image
docker pull ipfs/kubo

# Run IPFS in a Docker container
docker run -d --name ipfs-node -v ipfs-data:/data/ipfs -p 4001:4001 -p 8080:8080 -p 5001:5001 ipfs/kubo
```

You can test the IPFS connection using the provided script:

```bash
python test_ipfs.py
```

## Running the Application
1.Run with Docker

install docker and docker compose
```bash
docker-compose up --build
```
To stop the application:
```bash
docker-compose down
```

To rebuild after making changes:
```bash
docker-compose up --build
```
2.You can run the application using the provided run.py script:

```bash
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
streamlit run app/main.py
or
python run.py
```
- Backend: http://localhost:8000
- Frontend: http://localhost:8501
- IPFS: http://localhost:5001/webui
This will start all the required services (IPFS, backend, and frontend). You can also run specific components:

```bash
# Start only the backend
python run.py --frontend-only

# Start only the frontend
python run.py --backend-only

# Start without IPFS (if you already have IPFS running)
python run.py --no-ipfs
```

You can also check if the backend components are working correctly:

```bash
python check_backend.py
```

## pygroupsig Library

### Compilation

This library has been developed from scratch in Python _except_ for **mcl**.
We have built a wrapper around the original [mcl](https://github.com/herumi/mcl)
library written in C/C++ using Python ctypes.

> The library has type hints to ease the development of new schemes. If you encounter
> any errors or have suggestions for improvements, please feel free to open a PR or
> an issue.
>
> The library was tested in [mcl v2.00](https://github.com/herumi/mcl/tree/v2.00)

## Usage

You can instantiate the different schemes using the `group` class factory or by directly
using the specific class for each scheme:

```python
from pygroupsig import group, GroupBBS04, key, MemberKeyBBS04

## Two variants

# Method1
g = group("bbs04")() # Note: `group` function returns a class, not an instance
# Method2
# g = GroupBBS04()

g.setup()
gk_b64 = g.group_key.to_b64()

# Client side: create a group to use join protocol; you need to set the group_key (public)
gm = group("bbs04")()
gm.group_key.set_b64(gk_b64)

# Method 1
mk = key("bbs04", "member")()
# Method 2
# mk = MemberKeyBBS04()

# Test join protocol that take into account each scheme needs
msg2 = None
seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = g.join_mgr(msg2) # Group manager side
    msg2 = gm.join_mem(msg1, mk) # Member side

s_msg = gm.sign("Hello world!", mk)
v_msg = gm.verify("Hello world!", s_msg["signature"])
```

The functions `setup`, `join_mgr`, `join_mem`, `sign` and `verify` are common to all
schemes. Some schemes also implement additional functionalities:

### BBS04

- open

### PS16

- open
- open_verify

### CPY06

- open
- reveal
- trace
- prove_equality
- prove_equality_verify
- claim
- claim_verify

### KLAP20

- open
- open_verify

### GL19

- blind
- convert
- unblind

### DL21

- identify
- link
- link_verify

### DL21SEQ

- identify
- link
- link_verify
- seqlink
- seqlink_verify

## Tests

### Library Tests

Run the following command to execute the pygroupsig library tests:

```bash
python -m unittest
```

### System Tests

Run the following command to execute the healthcare data sharing system tests:

```bash
pytest tests/test_happy.py
```

This will run through the complete happy path scenario, testing all three workflows (storing, sharing, and purchasing).

## Acknowledgement

This work was supported by the European Commission under the Horizon Europe funding
programme, as part of the project SafeHorizon (Grant Agreement 101168562).
Moreover, it was supported by the European Commission under the Horizon Europe
Programme as part of the HEROES project (Grant Agreement number 101021801)
and the European Union's Internal Security Fund as part of the ALUNA project
(Grant Agreement number 101084929). Views and opinions expressed are however
those of the author(s) only and do not necessarily reflect those of the European.
Neither the European Union nor the granting authority can be held responsible for them.

- Based on [piotrszyma/mcl-python](https://github.com/piotrszyma/mcl-python) bindings for mcl.
- Based on [herumi/mcl](https://github.com/herumi/mcl).
- Based on [spirs/libgroupsig](https://gitlab.gicp.es/spirs/libgroupsig) and [IBM/libgroupsig](https://github.com/IBM/libgroupsig)

## LICENSE

```text
Copyright (c) 2024 Cybersecurity and Privacy Protection Research Group (GiCP), part of Consejo Superior de Investigaciones Científicas (CSIC). All rights reserved.
This work is licensed under the terms of the MIT license.
```

For a copy, see [LICENSE](LICENSE)
