// We require the Hardhat Runtime Environment explicitly here. This is optional
// but useful for running the script in a standalone fashion through `node <script>`.
const hre = require("hardhat");

async function main() {
  // Get the contract address from environment variable
  const contractAddress = process.env.CONTRACT_ADDRESS;
  if (!contractAddress) {
    console.error("Please set the CONTRACT_ADDRESS environment variable");
    process.exit(1);
  }

  console.log("Checking balance for contract:", contractAddress);

  // Get the contract balance
  const balance = await hre.ethers.provider.getBalance(contractAddress);
  console.log("Contract balance:", hre.ethers.utils.formatEther(balance), "ETH");

  // Get the contract instance
  const DataHub = await hre.ethers.getContractFactory("DataHub");
  const dataHub = DataHub.attach(contractAddress);

  // Get the contract owner
  const groupManager = await dataHub.groupManager();
  const revocationManager = await dataHub.revocationManager();
  console.log("Group Manager:", groupManager);
  console.log("Revocation Manager:", revocationManager);

  // Get the purchase count
  const seq = await dataHub.seq();
  console.log("Purchase count:", seq.toString());

  // Get the opening request count
  const openingRequestCount = await dataHub.openingRequestCount();
  console.log("Opening request count:", openingRequestCount.toString());

  // If there are purchases, show details of the latest one
  if (seq.toNumber() > 0) {
    const latestPurchase = await dataHub.purchases(seq);
    console.log("Latest purchase:");
    console.log("  Buyer:", latestPurchase.buyer);
    console.log("  Amount:", hre.ethers.utils.formatEther(latestPurchase.amount), "ETH");
    console.log("  Replied:", latestPurchase.replied);
    console.log("  Done:", latestPurchase.done);
  }

  // If there are opening requests, show details of the latest one
  if (openingRequestCount.toNumber() > 0) {
    const latestOpening = await dataHub.openingRequests(openingRequestCount);
    console.log("Latest opening request:");
    console.log("  Request ID:", latestOpening.requestId.toString());
    console.log("  Group Manager Approved:", latestOpening.groupManagerApproved);
    console.log("  Revocation Manager Approved:", latestOpening.revocationManagerApproved);
    console.log("  Completed:", latestOpening.completed);
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
