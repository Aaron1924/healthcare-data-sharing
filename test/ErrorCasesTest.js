const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Error Cases Test", function () {
  let dataHub;
  let owner, addr1, addr2;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    addr1 = signers[1];
    addr2 = signers[2];

    console.log("Owner address:", owner.address);
    console.log("Address 1:", addr1.address);
    console.log("Address 2:", addr2.address);

    // Deploy the contract
    const DataHub = await ethers.getContractFactory("DataHub");
    dataHub = await DataHub.deploy(owner.address, owner.address);

    console.log("DataHub deployed successfully");
  });

  describe("Role Management Error Cases", function () {
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
        dataHub.setGroupManager("0x0000000000000000000000000000000000000000")
      ).to.be.revertedWith("Invalid address");
    });

    it("Should revert when setting Revocation Manager to zero address", async function () {
      await expect(
        dataHub.setRevocationManager("0x0000000000000000000000000000000000000000")
      ).to.be.revertedWith("Invalid address");
    });
  });

  describe("Purchase Workflow Error Cases", function () {
    it("Should revert when requesting with zero value", async function () {
      const templateHash = ethers.utils.formatBytes32String("TemplateHash");

      await expect(
        dataHub.request(templateHash, { value: 0 })
      ).to.be.revertedWith("Escrow amount must be greater than 0");
    });

    it("Should revert when replying to an already replied request", async function () {
      // First create and reply to a request
      const templateHash = ethers.utils.formatBytes32String("TemplateHash");
      await dataHub.request(templateHash, { value: ethers.utils.parseEther("1.0") });
      await dataHub.reply(1, ethers.utils.formatBytes32String("TemplateCid"));

      // Try to reply again
      await expect(
        dataHub.reply(1, ethers.utils.formatBytes32String("TemplateCid2"))
      ).to.be.revertedWith("Request already replied to");
    });

    it("Should revert when non-buyer tries to finalize", async function () {
      await expect(
        dataHub.connect(addr1).finalize(1, true, [addr1.address])
      ).to.be.revertedWith("Only buyer can finalize");
    });

    it("Should revert when finalizing with no recipients for approval", async function () {
      await expect(
        dataHub.finalize(1, true, [])
      ).to.be.revertedWith("No recipients specified");
    });

    it("Should revert when finalizing an already finalized purchase", async function () {
      // Finalize the purchase
      await dataHub.finalize(1, false, [addr1.address]);

      // Try to finalize again
      await expect(
        dataHub.finalize(1, true, [addr1.address])
      ).to.be.revertedWith("Invalid purchase state");
    });
  });

  describe("Revocation Manager Error Cases", function () {
    it("Should revert when non-buyer tries to request opening", async function () {
      // First create a purchase request
      const templateHash = ethers.utils.formatBytes32String("TemplateHash2");
      await dataHub.request(templateHash, { value: ethers.utils.parseEther("1.0") });

      // Non-buyer tries to request opening
      await expect(
        dataHub.connect(addr1).requestOpening(ethers.utils.formatBytes32String("SignatureHash"), 2)
      ).to.be.revertedWith("Only the buyer can request opening");
    });

    it("Should revert when non-Group Manager tries to approve", async function () {
      // First create an opening request
      await dataHub.requestOpening(ethers.utils.formatBytes32String("SignatureHash"), 2);

      await expect(
        dataHub.connect(addr1).approveOpeningGroupManager(1)
      ).to.be.revertedWith("Only Group Manager can call this function");
    });

    it("Should revert when non-Revocation Manager tries to approve", async function () {
      await expect(
        dataHub.connect(addr1).approveOpeningRevocationManager(1)
      ).to.be.revertedWith("Only Revocation Manager can call this function");
    });

    it("Should revert when approving an already completed request", async function () {
      // First approve and complete an opening request
      await dataHub.approveOpeningGroupManager(1);
      await dataHub.approveOpeningRevocationManager(1);

      // Try to approve again
      await expect(
        dataHub.approveOpeningGroupManager(1)
      ).to.be.revertedWith("Request already completed");

      await expect(
        dataHub.approveOpeningRevocationManager(1)
      ).to.be.revertedWith("Request already completed");
    });
  });
});
