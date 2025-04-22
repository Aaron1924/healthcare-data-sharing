// hardhat.config.js
require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");
require("@nomicfoundation/hardhat-verify");
require('dotenv').config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  networks: {
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL || "https://api.developer.coinbase.com/rpc/v1/base-sepolia/TU79b5nxSoHEPVmNhElKsyBqt9CUbNTf",
      accounts: [
        // Default deployer account
        process.env.PRIVATE_KEY || "91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e",
        // Doctor/Buyer account
        process.env.DOCTOR_PRIVATE_KEY || "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        // Group Manager account
        process.env.GROUP_MANAGER_PRIVATE_KEY || "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        // Revocation Manager account
        process.env.REVOCATION_MANAGER_PRIVATE_KEY || "4bf1c7cac1c53c7f7f7ddcc979b159d66a3d2d721fa4053330adbb100be628a0"
      ],
      chainId: 84532,
    },
    hardhat: {
      accounts: [
        {
          privateKey: "91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e",
          balance: "10000000000000000000000"
        },
        {
          privateKey: "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
          balance: "10000000000000000000000"
        },
        {
          privateKey: "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
          balance: "10000000000000000000000"
        },
        {
          privateKey: "4bf1c7cac1c53c7f7f7ddcc979b159d66a3d2d721fa4053330adbb100be628a0",
          balance: "10000000000000000000000"
        }
      ]
    },
  },

  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },

  etherscan: {
    apiKey: {
      // Basescan doesn't require an API key for verification
      baseSepolia: "PLACEHOLDER",
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org",
        },
      },
    ],
  },
};
