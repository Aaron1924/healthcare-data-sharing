#!/bin/bash
# Script to compile the DataHub contract inside the Docker container

set -e  # Exit on error

echo "=== Setting up Hardhat and compiling contract ==="

# Create a temporary directory for Hardhat
mkdir -p /app/hardhat_temp
cd /app/hardhat_temp

# Initialize npm and install Hardhat
echo "Installing Hardhat..."
npm init -y
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox

# Initialize Hardhat
echo "Initializing Hardhat..."
npx hardhat init --basic

# Copy the contract to the contracts directory
echo "Copying DataHub.sol to contracts directory..."
mkdir -p contracts
cp /app/contracts/DataHub.sol contracts/

# Create hardhat.config.js
echo "Creating Hardhat configuration..."
cat > hardhat.config.js << 'EOL'
require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  paths: {
    artifacts: "../artifacts",
  },
};
EOL

# Compile the contract
echo "Compiling contract..."
npx hardhat compile

# Copy the artifacts to the main artifacts directory
echo "Copying artifacts to /app/artifacts..."
mkdir -p /app/artifacts
cp -r artifacts/* /app/artifacts/

# Clean up
echo "Cleaning up..."
cd /app
rm -rf /app/hardhat_temp

echo "=== Contract compilation complete ==="
echo "Artifacts are available in /app/artifacts/contracts/DataHub.sol/"
ls -la /app/artifacts/contracts/DataHub.sol/
