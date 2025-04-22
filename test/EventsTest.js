const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataHub Events Test", function () {
  let dataHub;
  let owner, addr1, addr2;

  before(async function () {
    // Get signers
    const signers = await ethers.getSigners();
    owner = signers[0];
    addr1 = signers[1];
    addr2 = signers[2];

    console.log("Owner address:", owner.address);

    // Deploy the contract
    const DataHub = await ethers.getContractFactory("DataHub");
    dataHub = await DataHub.deploy(owner.address, owner.address);

    console.log("DataHub deployed successfully");
  });

  describe("Event Emissions", function () {
    it("Should emit DataStored event", async function () {
      const cid = ethers.utils.formatBytes32String("QmTest");
      const merkleRoot = ethers.utils.formatBytes32String("MerkleRoot");
      const signature = ethers.utils.toUtf8Bytes("TestSignature");

      await expect(dataHub.storeData(cid, merkleRoot, signature))
        .to.emit(dataHub, "DataStored")
        .withArgs(merkleRoot, cid, owner.address);
    });

    it("Should emit RequestOpen event", async function () {
      const templateHash = ethers.utils.formatBytes32String("TemplateHash");
      const amount = ethers.utils.parseEther("1.0");

      await expect(dataHub.request(templateHash, { value: amount }))
        .to.emit(dataHub, "RequestOpen")
        .withArgs(1, templateHash, owner.address, amount);
    });

    it("Should emit ReplySubmitted event", async function () {
      const templateCid = ethers.utils.formatBytes32String("TemplateCid");

      await expect(dataHub.reply(1, templateCid))
        .to.emit(dataHub, "ReplySubmitted")
        .withArgs(1, templateCid, owner.address);
    });

    it("Should emit PaymentReleased event", async function () {
      const recipients = [addr1.address, addr2.address];

      await expect(dataHub.finalize(1, true, recipients))
        .to.emit(dataHub, "PaymentReleased")
        .withArgs(1, recipients);
    });

    it("Should emit OpeningRequested event", async function () {
      const signatureHash = ethers.utils.formatBytes32String("SignatureHash");

      // Create another purchase for this test
      const templateHash = ethers.utils.formatBytes32String("TemplateHash2");
      await dataHub.request(templateHash, { value: ethers.utils.parseEther("1.0") });

      await expect(dataHub.requestOpening(signatureHash, 2))
        .to.emit(dataHub, "OpeningRequested")
        .withArgs(1, signatureHash, 2, owner.address);
    });

    it("Should emit GroupManagerApproved event", async function () {
      await expect(dataHub.approveOpeningGroupManager(1))
        .to.emit(dataHub, "GroupManagerApproved")
        .withArgs(1);
    });

    it("Should emit RevocationManagerApproved and OpeningCompleted events", async function () {
      await expect(dataHub.approveOpeningRevocationManager(1))
        .to.emit(dataHub, "RevocationManagerApproved")
        .withArgs(1)
        .to.emit(dataHub, "OpeningCompleted")
        .withArgs(1);
    });
  });
});
