// We require the Hardhat Runtime Environment explicitly here. This is optional
// but useful for running the script in a standalone fashion through `node <script>`.
const hre = require("hardhat");

async function main() {
  // Get the contract factory
  const DataHub = await hre.ethers.getContractFactory("DataHub");

  // Get the Group Manager and Revocation Manager addresses from environment variables
  const groupManagerAddress = process.env.GROUP_MANAGER_ADDRESS || "0x70997970C51812dc3A010C7d01b50e0d17dc79C8";
  const revocationManagerAddress = process.env.REVOCATION_MANAGER_ADDRESS || "0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46";

  console.log("Group Manager Address:", groupManagerAddress);
  console.log("Revocation Manager Address:", revocationManagerAddress);

  // Deploy the contract
  console.log("Deploying DataHub contract...");
  const dataHub = await DataHub.deploy(groupManagerAddress, revocationManagerAddress);

  // Wait for deployment to finish
  await dataHub.deployed();

  // Get the contract address
  const dataHubAddress = dataHub.address;
  console.log("DataHub contract deployed to:", dataHubAddress);

  // Log deployment information for verification
  console.log("Network:", hre.network.name);
  console.log("Block number:", await hre.ethers.provider.getBlockNumber());

  // Add a delay to allow etherscan to index the contract
  console.log("Waiting for 30 seconds before verification...");
  await new Promise(resolve => setTimeout(resolve, 30000));

  // Verify the contract on etherscan (if not on a local network)
  if (hre.network.name !== "hardhat" && hre.network.name !== "localhost") {
    try {
      console.log("Verifying contract on Etherscan...");
      await hre.run("verify:verify", {
        address: dataHubAddress,
        constructorArguments: [groupManagerAddress, revocationManagerAddress],
      });
      console.log("Contract verified successfully");
    } catch (error) {
      console.error("Error verifying contract:", error);
      console.log("If verification failed, you may need to wait longer or verify manually with:");
      console.log(`npx hardhat verify --network ${hre.network.name} ${dataHubAddress} ${groupManagerAddress} ${revocationManagerAddress}`);
    }
  }
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
