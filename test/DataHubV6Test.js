const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Contract Tests (ethers v6)", function () {
  let dataHub;
  let owner, addr1, addr2, groupManager, revocationManager;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    addr1 = signers[1];
    addr2 = signers[2];
    groupManager = signers[3];
    revocationManager = signers[4];

    console.log("Owner address:", owner.address);
    console.log("Group Manager address:", groupManager.address);
    console.log("Revocation Manager address:", revocationManager.address);

    // Deploy the contract
    const DataHubFactory = await ethers.getContractFactory("DataHub");
    dataHub = await DataHubFactory.deploy(groupManager.address, revocationManager.address);
    
    // Wait for deployment
    await dataHub.waitForDeployment();
    console.log("DataHub deployed to:", await dataHub.getAddress());
  });

  it("Should set the correct group manager and revocation manager", async function () {
    expect(await dataHub.groupManager()).to.equal(groupManager.address);
    expect(await dataHub.revocationManager()).to.equal(revocationManager.address);
  });

  it("Should allow storing a record", async function () {
    const cid = ethers.encodeBytes32String("QmTest");
    const merkleRoot = ethers.encodeBytes32String("MerkleRoot");
    const signature = ethers.toUtf8Bytes("TestSignature");

    const tx = await dataHub.storeData(cid, merkleRoot, signature);
    await tx.wait();

    const record = await dataHub.records(merkleRoot);
    expect(record.cid).to.equal(cid);
    expect(record.merkleRoot).to.equal(merkleRoot);
    expect(record.owner).to.equal(owner.address);
  });

  it("Should create a purchase request", async function () {
    const templateHash = ethers.encodeBytes32String("TemplateHash");
    const amount = ethers.parseEther("1.0");

    const tx = await dataHub.request(templateHash, { value: amount });
    await tx.wait();

    const purchase = await dataHub.purchases(1);
    expect(purchase.buyer).to.equal(owner.address);
    expect(purchase.amount).to.equal(amount);
    expect(purchase.replied).to.equal(false);
    expect(purchase.done).to.equal(false);
  });

  it("Should reply to a purchase request", async function () {
    const templateCid = ethers.encodeBytes32String("TemplateCid");
    
    const tx = await dataHub.reply(1, templateCid);
    await tx.wait();

    const purchase = await dataHub.purchases(1);
    expect(purchase.replied).to.equal(true);
    expect(purchase.templateCid).to.equal(templateCid);
  });

  it("Should finalize a purchase", async function () {
    const recipients = [addr1.address, addr2.address];
    
    // Get initial balances
    const initialBalance1 = await ethers.provider.getBalance(addr1.address);
    const initialBalance2 = await ethers.provider.getBalance(addr2.address);

    const tx = await dataHub.finalize(1, true, recipients);
    await tx.wait();

    // Check that the purchase was finalized
    const purchase = await dataHub.purchases(1);
    expect(purchase.done).to.equal(true);

    // Check that the recipients received the payment
    const finalBalance1 = await ethers.provider.getBalance(addr1.address);
    const finalBalance2 = await ethers.provider.getBalance(addr2.address);

    const amount = ethers.parseEther("1.0");
    const expectedPayment = amount / BigInt(2); // Split between 2 recipients
    expect(finalBalance1 - initialBalance1).to.equal(expectedPayment);
    expect(finalBalance2 - initialBalance2).to.equal(expectedPayment);
  });

  it("Should allow requesting signature opening", async function () {
    // Create a new purchase request for this test
    const templateHash = ethers.encodeBytes32String("TemplateHash2");
    const amount = ethers.parseEther("1.0");
    
    let tx = await dataHub.request(templateHash, { value: amount });
    await tx.wait();

    // Request signature opening
    const signatureHash = ethers.encodeBytes32String("SignatureHash");
    tx = await dataHub.requestOpening(signatureHash, 2);
    await tx.wait();

    // Check that the opening request was created
    const openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.signatureHash).to.equal(signatureHash);
    expect(openingRequest.requestId).to.equal(2);
    expect(openingRequest.groupManagerApproved).to.equal(false);
    expect(openingRequest.revocationManagerApproved).to.equal(false);
    expect(openingRequest.completed).to.equal(false);
  });

  it("Should allow Group Manager to approve opening", async function () {
    // Group Manager approves
    const tx = await dataHub.connect(groupManager).approveOpeningGroupManager(1);
    await tx.wait();

    // Check that the opening request was updated
    const openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.groupManagerApproved).to.equal(true);
    expect(openingRequest.completed).to.equal(false);
  });

  it("Should allow Revocation Manager to approve opening and complete the request", async function () {
    // Revocation Manager approves
    const tx = await dataHub.connect(revocationManager).approveOpeningRevocationManager(1);
    await tx.wait();

    // Check that the opening request was completed
    const openingRequest = await dataHub.openingRequests(1);
    expect(openingRequest.revocationManagerApproved).to.equal(true);
    expect(openingRequest.completed).to.equal(true);
  });
});
