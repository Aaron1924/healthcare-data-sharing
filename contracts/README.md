# DataHub Smart Contract Deployment

This directory contains the DataHub smart contract for the Decentralized Healthcare Data Sharing system, along with deployment scripts and tests.

## Prerequisites

- Node.js (v14+)
- npm or yarn
- A wallet with Sepolia testnet ETH (get from [Sepolia Faucet](https://sepoliafaucet.com/) or [Alchemy Faucet](https://sepoliafaucet.com/))

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env` file in the root directory with the following variables:
   ```bash
   SEPOLIA_RPC_URL=https://rpc.sepolia.org
   PRIVATE_KEY=your_private_key_here
   ETHERSCAN_API_KEY=your_etherscan_api_key_here  # Get from https://etherscan.io/myapikey
   ```

## Compile Contract

```bash
npm run compile
```

## Run Tests

```bash
npm test
```

## Deploy to Sepolia Testnet

```bash
npm run deploy:sepolia
```

This will:
1. Deploy the DataHub contract to Sepolia testnet
2. Log the contract address
3. Verify the contract on Etherscan

## Verify Contract Manually

If the automatic verification fails, you can verify the contract manually:

```bash
npm run verify:sepolia CONTRACT_ADDRESS
```

Replace `CONTRACT_ADDRESS` with the address of your deployed contract.

## After Deployment

After successful deployment, update the `CONTRACT_ADDRESS` in your `.env` file with the deployed contract address. This will allow your backend API to interact with the contract.
