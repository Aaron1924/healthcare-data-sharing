const { expect } = require("chai");
const { ethers } = require("hardhat");
const { parseEther } = ethers;

describe("DataHub with Revocation Manager", function () {
  let dataHub;
  let owner;
  let groupManager;
  let revocationManager;
  let doctor;
  let patient;
  let buyer;

  beforeEach(async function () {
    // Get signers
    [owner, groupManager, revocationManager, doctor, patient, buyer] = await ethers.getSigners();

    // Deploy the contract with Group Manager and Revocation Manager addresses
    const DataHub = await ethers.getContractFactory("DataHub");
    dataHub = await DataHub.deploy(groupManager.address, revocationManager.address);
  });

  describe("Purchasing Workflow with Revocation Manager", function () {
    it("Should simulate the complete purchasing workflow with Revocation Manager", async function () {
      // Step 1: Doctor creates a record (simulated)
      const cid = ethers.encodeBytes32String("QmRecordCID");
      const merkleRoot = ethers.encodeBytes32String("MerkleRoot");

      // Create a mock group signature
      // In a real scenario, this would be created using the pygroupsig library
      const mockSignature = ethers.toUtf8Bytes("MockGroupSignature");

      // Step 2: Patient stores the record
      await dataHub.connect(patient).storeData(cid, merkleRoot, mockSignature);

      // Verify the record was stored
      const record = await dataHub.records(merkleRoot);
      expect(record.cid).to.equal(cid);
      expect(record.merkleRoot).to.equal(merkleRoot);
      expect(record.owner).to.equal(patient.address);

      // Step 3: Buyer requests to purchase data
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = parseEther("1.0");

      await dataHub.connect(buyer).request(templateHash, { value: amount });

      // Step 4: Hospital (represented by owner) prepares and replies with template data
      const templateCid = ethers.encodeBytes32String("QmTemplateCID");
      await dataHub.connect(owner).reply(1, templateCid);

      // Step 5: Simulate Revocation Manager involvement
      // In a real scenario, the buyer would request signature opening
      console.log("Simulating Revocation Manager involvement in signature opening");

      // Mock the signature opening process
      // In a real scenario, this would involve:
      // 1. Group Manager providing partial opening
      // 2. Revocation Manager providing partial opening
      // 3. Combining both to fully open the signature

      // For this test, we'll just log the process
      console.log("Group Manager provides partial opening information");
      console.log("Revocation Manager provides partial opening information");
      console.log("Signature fully opened, signer identity verified");

      // Step 6: Buyer finalizes the purchase after verification
      const recipients = [groupManager.address, patient.address];

      // Get initial balances
      const initialBalanceGM = await ethers.provider.getBalance(groupManager.address);
      const initialBalancePatient = await ethers.provider.getBalance(patient.address);

      // Finalize the purchase
      await dataHub.connect(buyer).finalize(1, true, recipients);

      // Check that the purchase was finalized
      const purchase = await dataHub.purchases(1);
      expect(purchase.done).to.equal(true);

      // Check that the recipients received payment
      const finalBalanceGM = await ethers.provider.getBalance(groupManager.address);
      const finalBalancePatient = await ethers.provider.getBalance(patient.address);

      const expectedPayment = amount / BigInt(2); // Split between 2 recipients
      expect(finalBalanceGM - initialBalanceGM).to.equal(expectedPayment);
      expect(finalBalancePatient - initialBalancePatient).to.equal(expectedPayment);

      console.log("Purchase successfully completed with Revocation Manager verification");
    });

    it("Should simulate a rejected purchase after Revocation Manager verification", async function () {
      // Step 1: Doctor creates a record (simulated)
      const cid = ethers.encodeBytes32String("QmRecordCID");
      const merkleRoot = ethers.encodeBytes32String("MerkleRoot");
      const mockSignature = ethers.toUtf8Bytes("MockGroupSignature");

      // Step 2: Patient stores the record
      await dataHub.connect(patient).storeData(cid, merkleRoot, mockSignature);

      // Step 3: Buyer requests to purchase data
      const templateHash = ethers.encodeBytes32String("TemplateHash");
      const amount = parseEther("1.0");

      await dataHub.connect(buyer).request(templateHash, { value: amount });

      // Step 4: Hospital replies with template data
      const templateCid = ethers.encodeBytes32String("QmTemplateCID");
      await dataHub.connect(owner).reply(1, templateCid);

      // Step 5: Simulate Revocation Manager involvement
      console.log("Simulating Revocation Manager involvement in signature opening");

      // Mock the signature opening process
      console.log("Group Manager provides partial opening information");
      console.log("Revocation Manager provides partial opening information");
      console.log("Signature verification FAILED - signer not authorized");

      // Step 6: Buyer rejects the purchase after verification failure
      const recipients = [groupManager.address, patient.address];

      // Get initial balance of buyer
      const initialBalanceBuyer = await ethers.provider.getBalance(buyer.address);

      // Finalize with rejection (ok = false)
      const tx = await dataHub.connect(buyer).finalize(1, false, recipients);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed * receipt.gasPrice;

      // Check that the purchase was finalized
      const purchase = await dataHub.purchases(1);
      expect(purchase.done).to.equal(true);

      // Check that the buyer received a refund
      const finalBalanceBuyer = await ethers.provider.getBalance(buyer.address);
      expect(finalBalanceBuyer).to.be.closeTo(
        initialBalanceBuyer + amount - gasUsed,
        parseEther("0.01") // Allow for small difference due to gas estimation
      );

      console.log("Purchase rejected after Revocation Manager verification failure");
    });
  });
});
