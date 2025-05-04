const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Contract Tests", function () {
  let dataHub;
  let owner, addr1, addr2, groupManager, revocationManager;

  beforeEach(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    addr1 = signers[1];
    addr2 = signers[2];
    groupManager = signers[3];
    revocationManager = signers[4];

    // Deploy the contract
    const DataHubFactory = await ethers.getContractFactory("DataHub");
    dataHub = await DataHubFactory.deploy(groupManager.address, revocationManager.address);
  });

  describe("Basic Functionality", function () {
    it("Should set the correct group manager and revocation manager", async function () {
      expect(await dataHub.groupManager()).to.equal(groupManager.address);
      expect(await dataHub.revocationManager()).to.equal(revocationManager.address);
    });

    it("Should allow storing a record", async function () {
      const cid = ethers.encodeBytes32String("QmTest");
      const merkleRoot = ethers.encodeBytes32String("MerkleRoot");
      const signature = ethers.toUtf8Bytes("TestSignature");

      await expect(dataHub.storeData(cid, merkleRoot, signature))
        .to.emit(dataHub, "DataStored")
        .withArgs(merkleRoot, cid, owner.address);

      const record = await dataHub.records(merkleRoot);
      expect(record.cid).to.equal(cid);
      expect(record.merkleRoot).to.equal(merkleRoot);
      expect(record.owner).to.equal(owner.address);
    });
  });

  describe("Purchase Workflow", function () {
    it("Should create and finalize a purchase", async function () {
      // Create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");

      await expect(dataHub.request(templateHash, { value: amount }))
        .to.emit(dataHub, "RequestOpen")
        .withArgs(1, templateHash, owner.address, amount);

      // Reply to the purchase request
      const templateCid = ethers.encodeBytes32String("TemplateCid");
      await expect(dataHub.reply(1, templateCid))
        .to.emit(dataHub, "ReplySubmitted")
        .withArgs(1, templateCid, owner.address);

      // Finalize the purchase
      const recipients = [addr1.address, addr2.address];

      // Get initial balances
      const initialBalance1 = await ethers.provider.getBalance(addr1.address);
      const initialBalance2 = await ethers.provider.getBalance(addr2.address);

      await expect(dataHub.finalize(1, true, recipients))
        .to.emit(dataHub, "PaymentReleased");

      // Check that the purchase was finalized
      const purchase = await dataHub.purchases(1);
      expect(purchase.done).to.equal(true);

      // Check that the recipients received the payment
      const finalBalance1 = await ethers.provider.getBalance(addr1.address);
      const finalBalance2 = await ethers.provider.getBalance(addr2.address);

      const expectedPayment = amount / BigInt(2); // Split between 2 recipients
      expect(finalBalance1 - initialBalance1).to.equal(expectedPayment);
      expect(finalBalance2 - initialBalance2).to.equal(expectedPayment);
    });

    it("Should refund the buyer when rejecting a purchase", async function () {
      // Create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");

      await dataHub.request(templateHash, { value: amount });

      // Reply to the purchase request
      const templateCid = ethers.encodeBytes32String("TemplateCid");
      await dataHub.reply(1, templateCid);

      // Get initial balance
      const initialBalance = await ethers.provider.getBalance(owner.address);

      // Finalize with rejection (ok = false)
      const tx = await dataHub.finalize(1, false, [addr1.address]);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed * receipt.gasPrice;

      // Check that the purchase was finalized
      const purchase = await dataHub.purchases(1);
      expect(purchase.done).to.equal(true);

      // Check that the buyer received the refund
      const finalBalance = await ethers.provider.getBalance(owner.address);
      expect(finalBalance).to.be.closeTo(
        initialBalance + amount - gasUsed,
        ethers.parseEther("0.01") // Allow for small difference due to gas estimation
      );
    });
  });

  describe("Revocation Manager Functionality", function () {
    it("Should allow requesting signature opening", async function () {
      // First create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");
      await dataHub.request(templateHash, { value: amount });

      // Request signature opening
      const signatureHash = ethers.encodeBytes32String("SignatureHash");
      await expect(dataHub.requestOpening(signatureHash, 1))
        .to.emit(dataHub, "OpeningRequested")
        .withArgs(1, signatureHash, 1, owner.address);

      // Check that the opening request was created
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.signatureHash).to.equal(signatureHash);
      expect(openingRequest.requestId).to.equal(1);
      expect(openingRequest.groupManagerApproved).to.equal(false);
      expect(openingRequest.revocationManagerApproved).to.equal(false);
      expect(openingRequest.completed).to.equal(false);
    });

    it("Should allow Group Manager to approve opening", async function () {
      // First create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");
      await dataHub.request(templateHash, { value: amount });

      // Request signature opening
      const signatureHash = ethers.encodeBytes32String("SignatureHash");
      await dataHub.requestOpening(signatureHash, 1);

      // Group Manager approves
      await expect(dataHub.connect(groupManager).approveOpeningGroupManager(1))
        .to.emit(dataHub, "GroupManagerApproved")
        .withArgs(1);

      // Check that the opening request was updated
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.groupManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(false);
    });

    it("Should allow Revocation Manager to approve opening", async function () {
      // First create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");
      await dataHub.request(templateHash, { value: amount });

      // Request signature opening
      const signatureHash = ethers.encodeBytes32String("SignatureHash");
      await dataHub.requestOpening(signatureHash, 1);

      // Revocation Manager approves
      await expect(dataHub.connect(revocationManager).approveOpeningRevocationManager(1))
        .to.emit(dataHub, "RevocationManagerApproved")
        .withArgs(1);

      // Check that the opening request was updated
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(false);
    });

    it("Should complete opening when both managers approve", async function () {
      // First create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");
      await dataHub.request(templateHash, { value: amount });

      // Request signature opening
      const signatureHash = ethers.encodeBytes32String("SignatureHash");
      await dataHub.requestOpening(signatureHash, 1);

      // Group Manager approves
      await dataHub.connect(groupManager).approveOpeningGroupManager(1);

      // Revocation Manager approves
      await expect(dataHub.connect(revocationManager).approveOpeningRevocationManager(1))
        .to.emit(dataHub, "OpeningCompleted")
        .withArgs(1);

      // Check that the opening request was completed
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.groupManagerApproved).to.equal(true);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(true);
    });

    it("Should complete opening when approvals happen in reverse order", async function () {
      // First create a purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = ethers.parseEther("1.0");
      await dataHub.request(templateHash, { value: amount });

      // Request signature opening
      const signatureHash = ethers.encodeBytes32String("SignatureHash");
      await dataHub.requestOpening(signatureHash, 1);

      // Revocation Manager approves first
      await dataHub.connect(revocationManager).approveOpeningRevocationManager(1);

      // Group Manager approves second
      await expect(dataHub.connect(groupManager).approveOpeningGroupManager(1))
        .to.emit(dataHub, "OpeningCompleted")
        .withArgs(1);

      // Check that the opening request was completed
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.groupManagerApproved).to.equal(true);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(true);
    });
  });
});
