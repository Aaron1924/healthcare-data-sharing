const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Minimal DataHub Test", function () {
  let dataHub;
  let owner, groupManager, revocationManager, patient, buyer;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    groupManager = signers[1];
    revocationManager = signers[2];
    patient = signers[3];
    buyer = signers[4];

    console.log("Owner address:", owner.address);
    console.log("Group Manager address:", groupManager.address);
    console.log("Revocation Manager address:", revocationManager.address);

    // Deploy the contract
    const DataHub = await ethers.getContractFactory("DataHub");
    // Use owner as both group manager and revocation manager for simplicity in testing
    dataHub = await DataHub.deploy(owner.address, owner.address);

    // Basic verification
    expect(await dataHub.groupManager()).to.equal(owner.address);
    expect(await dataHub.revocationManager()).to.equal(owner.address);

    console.log("DataHub deployed successfully");
  });

  it("Should store a record", async function () {
    const cid = ethers.utils.formatBytes32String("QmTest");
    const merkleRoot = ethers.utils.formatBytes32String("MerkleRoot");
    const signature = ethers.utils.toUtf8Bytes("TestSignature");

    // Patient stores a record
    await dataHub.connect(patient).storeData(cid, merkleRoot, signature);

    // Verify the record was stored
    const record = await dataHub.records(merkleRoot);
    expect(record.cid).to.equal(cid);
    expect(record.merkleRoot).to.equal(merkleRoot);
    expect(record.owner).to.equal(patient.address);

    console.log("Record stored successfully");
  });

  it("Should create a purchase request", async function () {
    const templateHash = ethers.utils.formatBytes32String("TemplateHash");
    const amount = ethers.utils.parseEther("1.0");

    // Buyer creates a purchase request - using the owner for simplicity
    // In a real scenario, we would use the buyer account
    await dataHub.request(templateHash, { value: amount });

    // Verify the purchase request was created
    const purchase = await dataHub.purchases(1);
    expect(purchase.buyer).to.equal(owner.address);
    expect(purchase.amount).to.equal(amount);

    console.log("Purchase request created successfully");
  });

  it("Should request signature opening", async function () {
    const signatureHash = ethers.utils.formatBytes32String("SignatureHash");

    // Owner requests signature opening (as the buyer)
    await dataHub.requestOpening(signatureHash, 1);

    // Verify the opening request was created
    let openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.signatureHash).to.equal(signatureHash);
    expect(openingRequest.requestId).to.equal(1n);

    console.log("Opening request created successfully");
  });

  it("Should allow Group Manager to approve opening", async function () {
    // For testing purposes, we'll use the owner to call the Group Manager function
    // In a real scenario, we would use the actual Group Manager account
    // This works because we set the owner as the Group Manager in the constructor
    await dataHub.approveOpeningGroupManager(1);

    // Verify the Group Manager approval
    const openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.groupManagerApproved).to.equal(true);

    console.log("Group Manager approved successfully");
  });

  it("Should allow Revocation Manager to approve opening", async function () {
    // For testing purposes, we'll use the owner to call the Revocation Manager function
    // In a real scenario, we would use the actual Revocation Manager account
    // This works because we set the owner as the Revocation Manager in the constructor
    await dataHub.approveOpeningRevocationManager(1);

    // Verify the Revocation Manager approval and completion
    const openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.revocationManagerApproved).to.equal(true);
    expect(openingRequest.completed).to.equal(true);

    console.log("Revocation Manager approved and request completed successfully");
  });
});
