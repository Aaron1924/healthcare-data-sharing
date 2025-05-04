const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Complete Test Suite", function () {
  let dataHub;
  let owner, addr1, addr2, groupManager, revocationManager, patient, doctor, buyer;
  let dataHubAddress;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    addr1 = signers[1];
    addr2 = signers[2];
    groupManager = signers[3];
    revocationManager = signers[4];
    patient = signers[5];
    doctor = signers[6];
    buyer = signers[7];
    
    console.log("Owner address:", owner.address);
    console.log("Group Manager address:", groupManager.address);
    console.log("Revocation Manager address:", revocationManager.address);
    console.log("Patient address:", patient.address);
    console.log("Doctor address:", doctor.address);
    console.log("Buyer address:", buyer.address);
    
    // Deploy the contract
    const DataHub = await ethers.getContractFactory("DataHub");
    dataHub = await DataHub.deploy(groupManager.address, revocationManager.address);
    dataHubAddress = await dataHub.getAddress();
    console.log("DataHub deployed to:", dataHubAddress);
  });

  describe("Constructor and Role Management", function () {
    it("Should set the correct group manager and revocation manager", async function () {
      expect(await dataHub.groupManager()).to.equal(groupManager.address);
      expect(await dataHub.revocationManager()).to.equal(revocationManager.address);
    });

    it("Should allow Group Manager to update their address", async function () {
      // Group Manager updates their address to addr1
      await dataHub.connect(groupManager).setGroupManager(addr1.address);
      expect(await dataHub.groupManager()).to.equal(addr1.address);
      
      // Reset for other tests
      await dataHub.connect(addr1).setGroupManager(groupManager.address);
      expect(await dataHub.groupManager()).to.equal(groupManager.address);
    });

    it("Should allow Revocation Manager to update their address", async function () {
      // Revocation Manager updates their address to addr2
      await dataHub.connect(revocationManager).setRevocationManager(addr2.address);
      expect(await dataHub.revocationManager()).to.equal(addr2.address);
      
      // Reset for other tests
      await dataHub.connect(addr2).setRevocationManager(revocationManager.address);
      expect(await dataHub.revocationManager()).to.equal(revocationManager.address);
    });

    it("Should revert when non-Group Manager tries to update Group Manager", async function () {
      await expect(
        dataHub.connect(addr1).setGroupManager(addr2.address)
      ).to.be.revertedWith("Only current Group Manager can update");
    });

    it("Should revert when non-Revocation Manager tries to update Revocation Manager", async function () {
      await expect(
        dataHub.connect(addr1).setRevocationManager(addr2.address)
      ).to.be.revertedWith("Only current Revocation Manager can update");
    });

    it("Should revert when setting Group Manager to zero address", async function () {
      await expect(
        dataHub.connect(groupManager).setGroupManager(ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid address");
    });

    it("Should revert when setting Revocation Manager to zero address", async function () {
      await expect(
        dataHub.connect(revocationManager).setRevocationManager(ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid address");
    });
  });

  describe("Storing Data", function () {
    it("Should store a record and emit an event", async function () {
      const cid = ethers.encodeBytes32String("QmTest1");
      const merkleRoot = ethers.encodeBytes32String("MerkleRoot1");
      const signature = ethers.toUtf8Bytes("TestSignature1");

      // Patient stores a record
      await expect(dataHub.connect(patient).storeData(cid, merkleRoot, signature))
        .to.emit(dataHub, "DataStored")
        .withArgs(merkleRoot, cid, patient.address);

      // Verify the record was stored
      const record = await dataHub.records(merkleRoot);
      expect(record.cid).to.equal(cid);
      expect(record.merkleRoot).to.equal(merkleRoot);
      expect(record.owner).to.equal(patient.address);
      
      // Check that timestamp is reasonable (within last minute)
      const now = Math.floor(Date.now() / 1000);
      expect(record.timestamp).to.be.closeTo(BigInt(now), BigInt(60));
    });

    it("Should allow multiple patients to store records", async function () {
      const cid = ethers.encodeBytes32String("QmTest2");
      const merkleRoot = ethers.encodeBytes32String("MerkleRoot2");
      const signature = ethers.toUtf8Bytes("TestSignature2");

      // Another patient (addr1) stores a record
      await dataHub.connect(addr1).storeData(cid, merkleRoot, signature);

      // Verify the record was stored
      const record = await dataHub.records(merkleRoot);
      expect(record.cid).to.equal(cid);
      expect(record.merkleRoot).to.equal(merkleRoot);
      expect(record.owner).to.equal(addr1.address);
    });
  });

  describe("Purchase Workflow", function () {
    it("Should create a purchase request and emit an event", async function () {
      const templateHash = ethers.encodeBytes32String("TemplateHash1");
      const amount = ethers.parseEther("1.0");

      // Buyer creates a purchase request
      await expect(dataHub.connect(buyer).request(templateHash, { value: amount }))
        .to.emit(dataHub, "RequestOpen")
        .withArgs(1, templateHash, buyer.address, amount);

      // Verify the purchase request was created
      const purchase = await dataHub.purchases(1);
      expect(purchase.buyer).to.equal(buyer.address);
      expect(purchase.amount).to.equal(amount);
      expect(purchase.replied).to.equal(false);
      expect(purchase.done).to.equal(false);
      
      // Check that sequence number was incremented
      expect(await dataHub.seq()).to.equal(1);
    });

    it("Should revert when requesting with zero value", async function () {
      const templateHash = ethers.encodeBytes32String("TemplateHash2");
      
      // Attempt to create purchase request with zero value
      await expect(
        dataHub.connect(buyer).request(templateHash, { value: 0 })
      ).to.be.revertedWith("Escrow amount must be greater than 0");
    });

    it("Should reply to a purchase request and emit an event", async function () {
      const templateCid = ethers.encodeBytes32String("TemplateCid1");
      
      // Hospital replies to the purchase request
      await expect(dataHub.connect(owner).reply(1, templateCid))
        .to.emit(dataHub, "ReplySubmitted")
        .withArgs(1, templateCid, owner.address);
      
      // Verify the purchase request was updated
      const purchase = await dataHub.purchases(1);
      expect(purchase.replied).to.equal(true);
      expect(purchase.templateCid).to.equal(templateCid);
    });

    it("Should revert when replying to an already replied request", async function () {
      const templateCid = ethers.encodeBytes32String("TemplateCid2");
      
      // Attempt to reply again
      await expect(
        dataHub.connect(owner).reply(1, templateCid)
      ).to.be.revertedWith("Request already replied to");
    });

    it("Should create another purchase request for testing", async function () {
      const templateHash = ethers.encodeBytes32String("TemplateHash3");
      const amount = ethers.parseEther("2.0");

      // Create another purchase request
      await dataHub.connect(buyer).request(templateHash, { value: amount });
      
      // Verify the purchase request was created
      const purchase = await dataHub.purchases(2);
      expect(purchase.buyer).to.equal(buyer.address);
      expect(purchase.amount).to.equal(amount);
      
      // Reply to this request
      const templateCid = ethers.encodeBytes32String("TemplateCid3");
      await dataHub.connect(owner).reply(2, templateCid);
    });

    it("Should finalize a purchase with approval and distribute payment", async function () {
      const recipients = [addr1.address, addr2.address];
      
      // Get initial balances
      const initialBalance1 = await ethers.provider.getBalance(addr1.address);
      const initialBalance2 = await ethers.provider.getBalance(addr2.address);

      // Buyer finalizes the purchase with approval
      await expect(dataHub.connect(buyer).finalize(1, true, recipients))
        .to.emit(dataHub, "PaymentReleased");

      // Verify the purchase was finalized
      const purchase = await dataHub.purchases(1);
      expect(purchase.done).to.equal(true);

      // Verify the recipients received payment
      const finalBalance1 = await ethers.provider.getBalance(addr1.address);
      const finalBalance2 = await ethers.provider.getBalance(addr2.address);

      const amount = ethers.parseEther("1.0");
      const expectedPayment = amount / BigInt(2); // Split between 2 recipients
      expect(finalBalance1 - initialBalance1).to.equal(expectedPayment);
      expect(finalBalance2 - initialBalance2).to.equal(expectedPayment);
    });

    it("Should finalize a purchase with rejection and refund buyer", async function () {
      // Get initial balance of buyer
      const initialBalance = await ethers.provider.getBalance(buyer.address);

      // Buyer finalizes the purchase with rejection
      const tx = await dataHub.connect(buyer).finalize(2, false, [addr1.address]);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed * receipt.gasPrice;

      // Verify the purchase was finalized
      const purchase = await dataHub.purchases(2);
      expect(purchase.done).to.equal(true);

      // Verify the buyer received a refund
      const finalBalance = await ethers.provider.getBalance(buyer.address);
      const amount = ethers.parseEther("2.0");
      expect(finalBalance).to.be.closeTo(
        initialBalance + amount - gasUsed,
        ethers.parseEther("0.01") // Allow for small difference due to gas estimation
      );
    });

    it("Should revert when non-buyer tries to finalize", async function () {
      // Create a new purchase request
      const templateHash = ethers.encodeBytes32String("TemplateHash4");
      await dataHub.connect(buyer).request(templateHash, { value: ethers.parseEther("1.0") });
      
      // Reply to the request
      await dataHub.connect(owner).reply(3, ethers.encodeBytes32String("TemplateCid4"));
      
      // Non-buyer tries to finalize
      await expect(
        dataHub.connect(addr1).finalize(3, true, [addr1.address])
      ).to.be.revertedWith("Only buyer can finalize");
    });

    it("Should revert when finalizing with no recipients for approval", async function () {
      await expect(
        dataHub.connect(buyer).finalize(3, true, [])
      ).to.be.revertedWith("No recipients specified");
    });

    it("Should revert when finalizing an already finalized purchase", async function () {
      // Finalize the purchase
      await dataHub.connect(buyer).finalize(3, false, [addr1.address]);
      
      // Try to finalize again
      await expect(
        dataHub.connect(buyer).finalize(3, true, [addr1.address])
      ).to.be.revertedWith("Invalid purchase state");
    });

    it("Should handle uneven payment splits correctly", async function () {
      // Create a new purchase request with an odd amount
      const templateHash = ethers.encodeBytes32String("TemplateHash5");
      const amount = ethers.parseEther("1.0") + BigInt(1); // 1 ETH + 1 wei
      
      await dataHub.connect(buyer).request(templateHash, { value: amount });
      await dataHub.connect(owner).reply(4, ethers.encodeBytes32String("TemplateCid5"));
      
      // Get initial balances
      const initialBalance1 = await ethers.provider.getBalance(addr1.address);
      const initialBalance2 = await ethers.provider.getBalance(addr2.address);
      const initialBalance3 = await ethers.provider.getBalance(owner.address);
      
      // Three recipients for uneven split
      const recipients = [addr1.address, addr2.address, owner.address];
      
      // Finalize with approval
      const tx = await dataHub.connect(buyer).finalize(4, true, recipients);
      await tx.wait();
      
      // Verify the recipients received payment
      const finalBalance1 = await ethers.provider.getBalance(addr1.address);
      const finalBalance2 = await ethers.provider.getBalance(addr2.address);
      const finalBalance3 = await ethers.provider.getBalance(owner.address);
      
      // Calculate expected payment (integer division)
      const expectedPayment = amount / BigInt(3);
      expect(finalBalance1 - initialBalance1).to.equal(expectedPayment);
      expect(finalBalance2 - initialBalance2).to.equal(expectedPayment);
      
      // Check for any remainder (should be very small due to integer division)
      const contractBalance = await ethers.provider.getBalance(dataHubAddress);
      expect(contractBalance).to.be.lessThan(BigInt(3)); // At most 2 wei remainder
    });
  });

  describe("Sharing Workflow", function () {
    it("Should allow posting sharing information", async function () {
      const doctorAddress = doctor.address;
      const cid_share = ethers.encodeBytes32String("SharedCID");
      const encryptedKey = ethers.toUtf8Bytes("EncryptedKey");

      // Call postShare function
      await dataHub.connect(patient).postShare(doctorAddress, cid_share, encryptedKey);
      
      // Since postShare is a placeholder, we just verify it doesn't revert
      // In a real implementation, we would check for state changes or events
    });
  });

  describe("Revocation Manager Workflow", function () {
    it("Should create a purchase request for testing revocation", async function () {
      const templateHash = ethers.encodeBytes32String("TemplateHash6");
      const amount = ethers.parseEther("1.0");

      // Create a purchase request
      await dataHub.connect(buyer).request(templateHash, { value: amount });
      
      // Reply to the request
      await dataHub.connect(owner).reply(5, ethers.encodeBytes32String("TemplateCid6"));
    });

    it("Should allow buyer to request signature opening", async function () {
      const signatureHash = ethers.encodeBytes32String("SignatureHash1");
      
      // Buyer requests signature opening
      await expect(dataHub.connect(buyer).requestOpening(signatureHash, 5))
        .to.emit(dataHub, "OpeningRequested")
        .withArgs(1, signatureHash, 5, buyer.address);
      
      // Verify the opening request was created
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.signatureHash).to.equal(signatureHash);
      expect(openingRequest.requestId).to.equal(5);
      expect(openingRequest.groupManagerApproved).to.equal(false);
      expect(openingRequest.revocationManagerApproved).to.equal(false);
      expect(openingRequest.completed).to.equal(false);
      
      // Check that opening request count was incremented
      expect(await dataHub.openingRequestCount()).to.equal(1);
    });

    it("Should revert when non-buyer tries to request opening", async function () {
      const signatureHash = ethers.encodeBytes32String("SignatureHash2");
      
      // Non-buyer tries to request opening
      await expect(
        dataHub.connect(addr1).requestOpening(signatureHash, 5)
      ).to.be.revertedWith("Only the buyer can request opening");
    });

    it("Should allow Group Manager to approve opening", async function () {
      // Group Manager approves
      await expect(dataHub.connect(groupManager).approveOpeningGroupManager(1))
        .to.emit(dataHub, "GroupManagerApproved")
        .withArgs(1);
      
      // Verify the opening request was updated
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.groupManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(false);
    });

    it("Should revert when non-Group Manager tries to approve", async function () {
      await expect(
        dataHub.connect(addr1).approveOpeningGroupManager(1)
      ).to.be.revertedWith("Only Group Manager can call this function");
    });

    it("Should allow Revocation Manager to approve opening and complete the request", async function () {
      // Revocation Manager approves
      await expect(dataHub.connect(revocationManager).approveOpeningRevocationManager(1))
        .to.emit(dataHub, "RevocationManagerApproved")
        .withArgs(1)
        .to.emit(dataHub, "OpeningCompleted")
        .withArgs(1);
      
      // Verify the opening request was completed
      const openingRequest = await dataHub.openingRequests(1);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(true);
    });

    it("Should revert when non-Revocation Manager tries to approve", async function () {
      // Create another opening request
      const signatureHash = ethers.encodeBytes32String("SignatureHash3");
      await dataHub.connect(buyer).requestOpening(signatureHash, 5);
      
      await expect(
        dataHub.connect(addr1).approveOpeningRevocationManager(2)
      ).to.be.revertedWith("Only Revocation Manager can call this function");
    });

    it("Should revert when approving an already completed request", async function () {
      // Try to approve the first request again
      await expect(
        dataHub.connect(groupManager).approveOpeningGroupManager(1)
      ).to.be.revertedWith("Request already completed");
      
      await expect(
        dataHub.connect(revocationManager).approveOpeningRevocationManager(1)
      ).to.be.revertedWith("Request already completed");
    });

    it("Should complete opening when approvals happen in reverse order", async function () {
      // For the second opening request, approve in reverse order
      
      // Revocation Manager approves first
      await dataHub.connect(revocationManager).approveOpeningRevocationManager(2);
      
      // Verify the opening request was updated
      let openingRequest = await dataHub.openingRequests(2);
      expect(openingRequest.revocationManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(false);
      
      // Group Manager approves second
      await expect(dataHub.connect(groupManager).approveOpeningGroupManager(2))
        .to.emit(dataHub, "OpeningCompleted")
        .withArgs(2);
      
      // Verify the opening request was completed
      openingRequest = await dataHub.openingRequests(2);
      expect(openingRequest.groupManagerApproved).to.equal(true);
      expect(openingRequest.completed).to.equal(true);
    });
  });
});
