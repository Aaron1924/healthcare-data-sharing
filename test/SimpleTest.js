const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Simple Test", function () {
  let dataHub;
  let owner;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];

    console.log("Owner address:", owner.address);

    // Deploy the contract
    const DataHub = await ethers.getContractFactory("DataHub");
    dataHub = await DataHub.deploy(owner.address, owner.address);

    console.log("DataHub deployed successfully");
  });

  describe("Basic Functionality", function () {
    it("Should set the correct group manager and revocation manager", async function () {
      expect(await dataHub.groupManager()).to.equal(owner.address);
      expect(await dataHub.revocationManager()).to.equal(owner.address);
    });

    it("Should store a record", async function () {
      const cid = ethers.utils.formatBytes32String("QmTest");
      const merkleRoot = ethers.utils.formatBytes32String("MerkleRoot");
      const signature = ethers.utils.toUtf8Bytes("TestSignature");

      await dataHub.storeData(cid, merkleRoot, signature);

      const record = await dataHub.records(merkleRoot);
      expect(record.cid).to.equal(cid);
      expect(record.merkleRoot).to.equal(merkleRoot);
      expect(record.owner).to.equal(owner.address);
    });

    it("Should create a purchase request", async function () {
      const templateHash = ethers.utils.formatBytes32String("TemplateHash");
      const amount = ethers.utils.parseEther("1.0");

      await dataHub.request(templateHash, { value: amount });

      const purchase = await dataHub.purchases(1);
      expect(purchase.buyer).to.equal(owner.address);
      expect(purchase.amount).to.equal(amount);
    });

    it("Should reply to a purchase request", async function () {
      const templateCid = ethers.utils.formatBytes32String("TemplateCid");

      await dataHub.reply(1, templateCid);

      const purchase = await dataHub.purchases(1);
      expect(purchase.replied).to.equal(true);
      expect(purchase.templateCid).to.equal(templateCid);
    });

    it("Should request signature opening", async function () {
      const signatureHash = ethers.utils.formatBytes32String("SignatureHash");

      await dataHub.requestOpening(signatureHash, 1);

      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.signatureHash).to.equal(signatureHash);
      expect(openingRequest.requestId).to.equal(1n);
    });

    it("Should approve opening as Group Manager", async function () {
      await dataHub.approveOpeningGroupManager(1);

      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.groupManagerApproved).to.equal(true);
    });

    it("Should approve opening as Revocation Manager and complete", async function () {
      await dataHub.approveOpeningRevocationManager(1);

      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(true);
    });

    it("Should finalize a purchase", async function () {
      // Create a new purchase for this test
      const templateHash = ethers.utils.formatBytes32String("TemplateHash2");
      const amount = ethers.utils.parseEther("1.0");

      await dataHub.request(templateHash, { value: amount });
      await dataHub.reply(2, ethers.utils.formatBytes32String("TemplateCid2"));

      // Finalize with rejection to get refund (simpler to test)
      const initialBalance = await ethers.provider.getBalance(owner.address);

      const tx = await dataHub.finalize(2, false, [owner.address]);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed.mul(receipt.effectiveGasPrice);

      const finalBalance = await ethers.provider.getBalance(owner.address);

      // Should be close to initial balance + amount - gas
      expect(finalBalance).to.be.closeTo(
        initialBalance.add(amount).sub(gasUsed),
        ethers.utils.parseEther("0.01")
      );

      const purchase = await dataHub.purchases(2);
      expect(purchase.done).to.equal(true);
    });
  });
});
