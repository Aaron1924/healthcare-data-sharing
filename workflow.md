# Healthcare Data Sharing System Workflows

This document provides a detailed explanation of the three main workflows in our decentralized healthcare data sharing system: Storing, Sharing, and Purchasing. Each workflow is described step-by-step, including both on-chain and off-chain operations.

## 1. Storing Workflow

The storing workflow allows doctors to create medical records and store them securely for patients.

### Step 1: Doctor Creates a Medical Record
- **Actor**: Doctor
- **Actions**:
  - Doctor fills out a medical record form with patient information, diagnosis, treatment, etc.
  - The system generates a Merkle root hash (IDrec) of the record content
  - The doctor's wallet signs the transaction

### Step 2: Group Signature Creation
- **Actor**: System (Doctor's client)
- **Actions**:
  - The system uses the pygroupsig module with the CPY06 scheme
  - The doctor's group member secret key is used to sign the Merkle root
  - This creates a group signature (SD) that proves the doctor is a legitimate member without revealing identity

### Step 3: Record Encryption
- **Actor**: System (Doctor's client)
- **Actions**:
  - The record is encrypted with the patient's key (K_patient)
  - The hospital info and patient key are encrypted with the Group Manager's public key (PCS encryption)
  - This creates the EId component of the CERT

### Step 4: IPFS Upload
- **Actor**: System (Doctor's client)
- **Actions**:
  - The encrypted record is uploaded to IPFS
  - IPFS returns a Content Identifier (CID)

### Step 5: Blockchain Transaction
- **Actor**: Doctor's wallet
- **Actions**:
  - The doctor's wallet calls the `storeData(cid, merkleRoot, sig)` function on the DataHub smart contract
  - This transaction stores the record metadata on the blockchain
  - Gas fees are paid by the doctor's wallet

### Step 6: Event Emission
- **Actor**: Smart Contract
- **Actions**:
  - The contract emits a `DataStored` event with the CID, merkle root, and patient address
  - This event notifies the patient that a new record is available

### Step 7: Patient Notification
- **Actor**: Patient's client
- **Actions**:
  - The patient's application listens for `DataStored` events
  - When a new record is detected, it's automatically added to the patient's records list
  - The patient can view the decrypted record in their application

## 2. Sharing Workflow

The sharing workflow allows patients to securely share their medical records with specific doctors.

### Step 1: Patient Selects a Record to Share
- **Actor**: Patient
- **Actions**:
  - Patient selects a record from their list
  - The system retrieves the encrypted record from IPFS using the CID
  - The record is decrypted using the patient's key (K_patient)

### Step 2: Temporary Key Generation
- **Actor**: System (Patient's client)
- **Actions**:
  - A new temporary key (K_temp) is generated
  - The record is re-encrypted with this temporary key
  - The re-encrypted record is uploaded to IPFS, generating a new CID (cid_share)

### Step 3: Key Encryption
- **Actor**: System (Patient's client)
- **Actions**:
  - The temporary key (K_temp) is encrypted with the doctor's public key
  - This ensures only the intended doctor can decrypt the record

### Step 4: Sharing Information
- **Actor**: Patient
- **Actions**:
  - The patient sends the sharing information to the doctor
  - This includes the new CID (cid_share) and the encrypted temporary key (EK_temp)
  - This can be done off-chain via the API or optionally through the smart contract's `postShare` function

### Step 5: Doctor Access
- **Actor**: Doctor
- **Actions**:
  - The doctor receives the sharing information
  - The doctor decrypts the temporary key using their private key
  - The doctor uses the temporary key to decrypt the record
  - The doctor can now view the shared medical record

## 3. Purchasing Workflow

The purchasing workflow allows buyers to acquire anonymized medical data that matches specific criteria.

### Step 1: Buyer Creates a Purchase Request
- **Actor**: Buyer
- **Actions**:
  - Buyer creates a template with required fields (e.g., age, gender, diagnosis)
  - Buyer specifies criteria like category, time period, and minimum records
  - Buyer deposits escrow funds by calling `request(templateHash)` on the smart contract
  - The contract emits a `RequestOpen` event

### Step 2: Hospital Confirms Availability
- **Actor**: Hospital
- **Actions**:
  - Hospital backend monitors for `RequestOpen` events
  - Hospital checks if it has data matching the buyer's criteria
  - If data is available, hospital calls `reply(requestId, templateCid)` on the smart contract
  - The contract emits a `ReplySubmitted` event

### Step 3: Patient Template Filling
- **Actor**: Patient
- **Actions**:
  - Patient receives a notification about the data request
  - Patient reviews the request and decides whether to participate
  - If participating, the patient's system:
    - Selects matching records
    - Extracts the requested fields
    - Creates a template package with the data
    - Generates a Merkle proof for verification
    - Encrypts the template with a new temporary key
    - Encrypts the temporary key with the buyer's public key
    - Uploads the encrypted template to IPFS
    - Includes the CERT (with group signature) for verification

### Step 4: Buyer Verification
- **Actor**: Buyer
- **Actions**:
  - Buyer retrieves the template package
  - Buyer decrypts the temporary key using their private key
  - Buyer decrypts the template package
  - Buyer verifies the Merkle proofs to ensure data integrity
  - Buyer verifies the group signature to ensure the data came from a legitimate doctor
  - If verification fails, the buyer can call the Group Manager and Revocation Manager to identify the fraudulent doctor

### Step 5: Payment Finalization
- **Actor**: Buyer
- **Actions**:
  - If verification passes, buyer calls `finalize(requestId, true, recipients)` on the smart contract
  - The escrow payment is distributed to the hospital and participating patients
  - If verification fails, buyer calls `finalize(requestId, false)` to get a refund
  - The contract emits a `PaymentReleased` event

### Step 6: Transaction Recording
- **Actor**: System
- **Actions**:
  - All blockchain transactions are recorded with gas fees and other details
  - This information is displayed in the Gas Fees tab for each role
  - Transaction history can be exported for analysis

## Technical Implementation Details

### Group Signatures
- Uses the pygroupsig module with the CPY06 scheme
- Requires setup of:
  - Group public key
  - Group manager's secret key
  - Revocation manager's secret key
  - Doctor's group member secret key

### Encryption
- AES-GCM for symmetric encryption of records and templates
- RSA/ECIES for asymmetric encryption of temporary keys
- PCS encryption for the EId component of the CERT

### Storage
- IPFS for decentralized storage of encrypted records and templates
- Blockchain for storing metadata and handling payments
- Local storage as fallback when IPFS is unavailable

### Smart Contract
- Single Solidity contract (DataHub.sol) handling all three workflows
- Functions: storeData, request, reply, finalize
- Events: DataStored, RequestOpen, ReplySubmitted, PaymentReleased

### Transaction Tracking
- All blockchain transactions are tracked with:
  - Transaction hash
  - Gas used
  - Gas price
  - Operation type
  - Timestamp
  - Status

## Data Structures

### CERT Structure
```json
{
  "sig": "0x...",  // 362-byte group signature (hex)
  "eId": "0x..."   // PCS(hospitalInfo || K_patient)
}
```

### On-chain Record Metadata
```solidity
struct RecordMeta {
  bytes32 cid;        // IPFS CID (v1 hashed to bytes32)
  bytes32 merkleRoot; // idRec
  bytes   sig;        // group signature
  address owner;      // patient wallet
  uint256 timestamp;
}
```

### Purchase Request
```json
{
  "request_id": "uuid",
  "template_hash": "0x...",
  "amount": 0.1,
  "buyer": "0x...",
  "timestamp": 1234567890,
  "status": "pending|replied|filled|verified|finalized",
  "template": {
    "category": "Cardiology",
    "demographics": {
      "age": true,
      "gender": true,
      "location": false,
      "ethnicity": false
    },
    "medical_data": {
      "diagnosis": true,
      "treatment": true,
      "medications": false,
      "lab_results": false
    },
    "time_period": "1 year",
    "min_records": 20
  }
}
```

## Security Considerations

1. **Privacy**:
   - Doctor anonymity is preserved through group signatures
   - Patient data is always encrypted
   - Temporary keys ensure secure sharing

2. **Data Integrity**:
   - Merkle proofs verify data hasn't been tampered with
   - Group signatures verify data comes from legitimate doctors

3. **Economic Security**:
   - Escrow payments protect buyers from fraudulent data
   - Payment distribution incentivizes participation

4. **Revocation**:
   - Group Manager and Revocation Manager can identify fraudulent doctors
   - This provides accountability while maintaining privacy
