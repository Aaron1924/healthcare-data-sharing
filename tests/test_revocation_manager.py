import pytest
import os
import json
import ipfshttpclient
from web3 import Web3
import sys
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.backends import default_backend

# Add the project root to the path so we can import the backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules from the project
from backend.data import MerkleService, encrypt_record, decrypt_record
from backend.roles import Patient, Doctor, GroupManager, RevocationManager

# Import pygroupsig modules
try:
    from pygroupsig import group, key, message
except ImportError:
    print("Warning: pygroupsig module not found. Make sure it's installed and MCL_LIB_PATH is set.")
    # Create mock classes for testing without the actual library
    class group:
        @staticmethod
        def __call__(*args):
            return MockGroup()
    
    class key:
        @staticmethod
        def __call__(*args):
            return MockKey()
    
    class message:
        @staticmethod
        def __call__(*args):
            return MockMessage()
    
    class MockGroup:
        def __init__(self):
            self.group_key = MockKey()
        
        def setup(self):
            pass
        
        def join_mgr(self, msg):
            return "mock_msg"
        
        def join_mem(self, msg, key):
            return "mock_msg"
        
        def join_seq(self):
            return 1
        
        def sign(self, msg, key):
            return {"signature": "mock_signature"}
        
        def verify(self, msg, sig):
            return True
        
        def open(self, sig, group_manager_partial=None, revocation_manager_partial=None):
            if group_manager_partial and revocation_manager_partial:
                return {"signer": "mock_signer", "success": True}
            elif group_manager_partial:
                return {"partial_r": "mock_partial_r"}
            else:
                return {"partial_g": "mock_partial_g"}
    
    class MockKey:
        def set_b64(self, b64):
            pass
        
        def to_b64(self):
            return "mock_b64"
    
    class MockMessage:
        def set_bytes(self, bytes_data):
            pass

# Test constants
TEST_RECORD = {
    "patientID": "123",
    "date": "2025-04-18",
    "diagnosis": "Hypertension",
    "doctorID": "DOC789",
    "notes": "Patient advised to monitor blood pressure daily and start low-dose medication."
}

TEMPLATE_FIELDS = ["patientID", "diagnosis"]

HOSPITAL_INFO = "Hospital A, 123 Main St, Cityville"

# Initialize IPFS client
@pytest.fixture
def ipfs_client():
    try:
        return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
    except Exception as e:
        print(f"Warning: IPFS daemon not running: {e}")
        # Mock IPFS client for testing without actual IPFS
        class MockIPFSClient:
            def add_bytes(self, data):
                return {"Hash": hashlib.sha256(data).hexdigest()}
            
            def cat(self, cid):
                return b"mock_data"
        
        return MockIPFSClient()

# Initialize group signature
@pytest.fixture
def hospital_group():
    g = group("cpy06")()
    g.setup()
    return g

@pytest.fixture
def group_manager(hospital_group):
    # Create a Group Manager with access to the group
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return GroupManager(private_key=private_key, public_key=public_key, group=hospital_group)

@pytest.fixture
def revocation_manager(hospital_group):
    # Create a Revocation Manager with access to the group
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return RevocationManager(private_key=private_key, public_key=public_key, group=hospital_group)

@pytest.fixture
def doctor_key(hospital_group):
    doctor_key = key("cpy06", "member")()
    
    # Simulate join process
    gm = group("cpy06")()
    gm.group_key.set_b64(hospital_group.group_key.to_b64())
    
    msg2 = None
    seq = gm.join_seq()
    for _ in range(0, seq + 1, 2):
        msg1 = hospital_group.join_mgr(msg2)  # Group manager side
        msg2 = gm.join_mem(msg1, doctor_key)  # Member side
    
    return doctor_key, gm

@pytest.fixture
def patient():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return Patient(private_key=private_key, public_key=public_key)

@pytest.fixture
def doctor():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return Doctor(private_key=private_key, public_key=public_key)

@pytest.fixture
def buyer():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return {"private_key": private_key, "public_key": public_key}

def test_revocation_manager_integration(ipfs_client, hospital_group, doctor_key, patient, doctor, group_manager, revocation_manager, buyer):
    """
    Test the complete workflow including the Revocation Manager's role in the purchasing process
    """
    print("\n=== Starting Revocation Manager Integration Test ===")
    
    # === STEP 1: Doctor creates and signs a record ===
    print("\n--- Step 1: Doctor creates and signs a record ---")
    doctor_key_obj, doctor_group = doctor_key
    
    # Create Merkle tree from record
    merkle_service = MerkleService()
    merkle_root, proofs = merkle_service.create_merkle_tree(TEST_RECORD)
    print(f"Merkle Root: {merkle_root}")
    
    # Doctor signs the record using group signature
    signature_data = doctor_group.sign(merkle_root, doctor_key_obj)
    signature = signature_data["signature"]
    print(f"Record signed with group signature")
    
    # Verify the signature
    assert doctor_group.verify(merkle_root, signature)
    print(f"Signature verified successfully")
    
    # === STEP 2: Patient encrypts and stores the record ===
    print("\n--- Step 2: Patient encrypts and stores the record ---")
    key_patient = patient.generate_key()
    encrypted_record = encrypt_record(TEST_RECORD, key_patient)
    
    # Store on IPFS
    cid = ipfs_client.add_bytes(encrypted_record)["Hash"]
    print(f"Record stored on IPFS with CID: {cid}")
    
    # === STEP 3: Buyer requests to purchase data ===
    print("\n--- Step 3: Buyer requests to purchase data ---")
    template_hash = hashlib.sha256(json.dumps(TEMPLATE_FIELDS).encode()).hexdigest()
    print(f"Buyer requests data with template hash: {template_hash}")
    
    # === STEP 4: Hospital matches patients and prepares template data ===
    print("\n--- Step 4: Hospital matches patients and prepares template data ---")
    # Extract requested fields from the record
    template_data = {field: TEST_RECORD[field] for field in TEMPLATE_FIELDS}
    print(f"Template data prepared: {template_data}")
    
    # Patient encrypts the template data
    key_template = os.urandom(32)
    encrypted_template = encrypt_record(template_data, key_template)
    
    # Store encrypted template on IPFS
    template_cid = ipfs_client.add_bytes(encrypted_template)["Hash"]
    print(f"Template stored on IPFS with CID: {template_cid}")
    
    # === STEP 5: Buyer verifies the data and requests signature opening ===
    print("\n--- Step 5: Buyer verifies the data and requests signature opening ---")
    # Buyer would verify the Merkle proofs here
    
    # Buyer requests opening of the signature to verify the signer's identity
    print("Buyer requests opening of the signature")
    
    # === STEP 6: Group Manager provides partial opening ===
    print("\n--- Step 6: Group Manager provides partial opening ---")
    partial_g_result = hospital_group.open(signature)
    partial_g = partial_g_result["partial_g"]
    print(f"Group Manager provided partial opening")
    
    # === STEP 7: Revocation Manager provides partial opening ===
    print("\n--- Step 7: Revocation Manager provides partial opening ---")
    partial_r_result = hospital_group.open(signature, group_manager_partial=partial_g)
    partial_r = partial_r_result["partial_r"]
    print(f"Revocation Manager provided partial opening")
    
    # === STEP 8: Combine both partial results to fully open the signature ===
    print("\n--- Step 8: Combine both partial results to fully open the signature ---")
    full_open_result = hospital_group.open(
        signature,
        group_manager_partial=partial_g,
        revocation_manager_partial=partial_r
    )
    
    assert full_open_result["success"] == True
    print(f"Signature successfully opened, signer identified")
    
    # === STEP 9: Buyer finalizes the purchase ===
    print("\n--- Step 9: Buyer finalizes the purchase ---")
    print(f"Buyer approves the purchase and releases payment")
    
    # === STEP 10: Buyer decrypts the purchased data ===
    print("\n--- Step 10: Buyer decrypts the purchased data ---")
    # In a real scenario, the key_template would be encrypted with the buyer's public key
    # and sent to the buyer through a secure channel
    
    # Retrieve encrypted template from IPFS
    retrieved_encrypted_template = ipfs_client.cat(template_cid)
    
    # Decrypt the template
    decrypted_template = decrypt_record(retrieved_encrypted_template, key_template)
    print(f"Buyer successfully decrypted the purchased data: {decrypted_template}")
    
    # Verify the decrypted data matches the expected template
    for field in TEMPLATE_FIELDS:
        assert decrypted_template[field] == TEST_RECORD[field]
    
    print("\n=== Revocation Manager Integration Test Completed Successfully ===")
    
    return {
        "cid": cid,
        "template_cid": template_cid,
        "signature": signature,
        "partial_g": partial_g,
        "partial_r": partial_r
    }

if __name__ == "__main__":
    # This allows running the test directly with python tests/test_revocation_manager.py
    pytest.main(["-xvs", __file__])
