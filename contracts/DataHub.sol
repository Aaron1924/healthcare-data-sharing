// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataHub {
    struct RecordMeta {
        bytes32 cid;        // IPFS CID (v1 hashed to bytes32)
        bytes32 merkleRoot; // idRec
        bytes   sig;        // group signature
        address owner;      // patient wallet
        uint256 timestamp;
    }

    mapping(bytes32 => RecordMeta) public records; // key = merkleRoot

    // minimal escrow for purchasing
    struct Purchase {
        address buyer;
        uint256 amount;
        bool replied;
        bytes32 templateCid;
        bool done;
    }

    mapping(uint256 => Purchase) public purchases;
    uint256 public seq;

    // Add Revocation Manager role
    address public revocationManager;
    address public groupManager;

    // Constructor to set initial roles
    constructor(address _groupManager, address _revocationManager) {
        groupManager = _groupManager != address(0) ? _groupManager : msg.sender;
        revocationManager = _revocationManager != address(0) ? _revocationManager : msg.sender;
    }

    /**
     * @dev Update the Group Manager address
     * @param _groupManager New Group Manager address
     */
    function setGroupManager(address _groupManager) external {
        require(msg.sender == groupManager, "Only current Group Manager can update");
        require(_groupManager != address(0), "Invalid address");
        groupManager = _groupManager;
    }

    /**
     * @dev Update the Revocation Manager address
     * @param _revocationManager New Revocation Manager address
     */
    function setRevocationManager(address _revocationManager) external {
        require(msg.sender == revocationManager, "Only current Revocation Manager can update");
        require(_revocationManager != address(0), "Invalid address");
        revocationManager = _revocationManager;
    }

    // Modifiers for access control
    modifier onlyGroupManager() {
        require(msg.sender == groupManager, "Only Group Manager can call this function");
        _;
    }

    modifier onlyRevocationManager() {
        require(msg.sender == revocationManager, "Only Revocation Manager can call this function");
        _;
    }

    // Struct to track opening requests
    struct OpeningRequest {
        bytes32 signatureHash;
        uint256 requestId;  // Associated purchase request ID
        bool groupManagerApproved;
        bool revocationManagerApproved;
        bool completed;
    }

    mapping(uint256 => OpeningRequest) public openingRequests;
    uint256 public openingRequestCount;

    event DataStored(bytes32 merkleRoot, bytes32 cid, address indexed owner);
    event RequestOpen(uint256 id, bytes32 templateHash, address buyer, uint256 amount);
    event ReplySubmitted(uint256 id, bytes32 templateCid, address hospital);
    event PaymentReleased(uint256 id, address[] recipients);
    event OpeningRequested(uint256 openingId, bytes32 signatureHash, uint256 requestId, address requester);
    event GroupManagerApproved(uint256 requestId);
    event RevocationManagerApproved(uint256 requestId);
    event OpeningCompleted(uint256 requestId);

    /**
     * @dev Store a new health record
     * @param cid IPFS CID of the encrypted record
     * @param root Merkle root of the record
     * @param sig Group signature
     */
    function storeData(bytes32 cid, bytes32 root, bytes calldata sig) external {
        records[root] = RecordMeta(cid, root, sig, msg.sender, block.timestamp);
        emit DataStored(root, cid, msg.sender);
    }

    /**
     * @dev Request to purchase data
     * @param templateHash Hash of the requested data template
     * @return id Request ID
     */
    function request(bytes32 templateHash) external payable returns (uint256 id) {
        require(msg.value > 0, "Escrow amount must be greater than 0");
        id = ++seq;
        purchases[id] = Purchase(msg.sender, msg.value, false, 0x0, false);
        emit RequestOpen(id, templateHash, msg.sender, msg.value);
    }

    /**
     * @dev Reply to a purchase request
     * @param id Request ID
     * @param templateCid IPFS CID of the template data
     */
    function reply(uint256 id, bytes32 templateCid) external {
        Purchase storage p = purchases[id];
        require(!p.replied, "Request already replied to");
        p.replied = true;
        p.templateCid = templateCid;
        emit ReplySubmitted(id, templateCid, msg.sender);
    }

    /**
     * @dev Finalize a purchase
     * @param id Request ID
     * @param ok Whether to approve the purchase
     * @param recipients Recipients of the payment
     */
    function finalize(uint256 id, bool ok, address payable[] calldata recipients) external {
        Purchase storage p = purchases[id];
        require(!p.done && p.replied, "Invalid purchase state");
        require(msg.sender == p.buyer, "Only buyer can finalize");
        p.done = true;

        if (ok) {
            require(recipients.length > 0, "No recipients specified");
            uint256 split = p.amount / recipients.length;
            for (uint i = 0; i < recipients.length; i++) {
                recipients[i].transfer(split);
            }
        } else {
            payable(p.buyer).transfer(p.amount);
        }

        // Convert address payable[] to address[] for the event
        address[] memory recipientAddresses = new address[](recipients.length);
        for (uint i = 0; i < recipients.length; i++) {
            recipientAddresses[i] = recipients[i];
        }
        emit PaymentReleased(id, recipientAddresses);
    }

    /**
     * @dev Optional helper function to post sharing information
     * @param doctorAddress Doctor's wallet address
     * @param cid_share IPFS CID of the shared record
     * @param encryptedKey Encrypted temporary key
     */
    function postShare(address doctorAddress, bytes32 cid_share, bytes calldata encryptedKey) external {
        // This is a helper function that could be used to post sharing information on-chain
        // For the MVP, we'll handle sharing off-chain via the API
        // This function is included for future expansion
    }

    // Request to open a signature
    function requestOpening(bytes32 signatureHash, uint256 requestId) external returns (uint256) {
        require(purchases[requestId].buyer == msg.sender, "Only the buyer can request opening");

        uint256 openingId = ++openingRequestCount;
        openingRequests[openingId] = OpeningRequest({
            signatureHash: signatureHash,
            requestId: requestId,
            groupManagerApproved: false,
            revocationManagerApproved: false,
            completed: false
        });

        emit OpeningRequested(openingId, signatureHash, requestId, msg.sender);
        return openingId;
    }

    // Group Manager approves opening (after off-chain computation)
    function approveOpeningGroupManager(uint256 openingId) external onlyGroupManager {
        OpeningRequest storage openingReq = openingRequests[openingId];
        require(!openingReq.completed, "Request already completed");

        openingReq.groupManagerApproved = true;
        emit GroupManagerApproved(openingId);

        // Check if both have approved
        if (openingReq.revocationManagerApproved) {
            openingReq.completed = true;
            emit OpeningCompleted(openingId);
        }
    }

    // Revocation Manager approves opening (after off-chain computation)
    function approveOpeningRevocationManager(uint256 openingId) external onlyRevocationManager {
        OpeningRequest storage openingReq = openingRequests[openingId];
        require(!openingReq.completed, "Request already completed");

        openingReq.revocationManagerApproved = true;
        emit RevocationManagerApproved(openingId);

        // Check if both have approved
        if (openingReq.groupManagerApproved) {
            openingReq.completed = true;
            emit OpeningCompleted(openingId);
        }
    }
}

