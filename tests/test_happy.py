import pytest
import os
import json
import ipfshttpclient
from web3 import Web3
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from backend.data import MerkleService, encrypt_record, encrypt_hospital_info_and_key
from backend.roles import Patient, Doctor, GroupManager
from pygroupsig import group, key

# Test constants
TEST_RECORD = {
    "patientID": "123",
    "date": "2025-04-18",
    "diagnosis": "Hypertension",
    "doctorID": "DOC789",
    "notes": "Patient advised to monitor blood pressure daily and start low-dose medication."
}

HOSPITAL_INFO = "Hospital A, 123 Main St, Cityville"

# Initialize IPFS client
@pytest.fixture
def ipfs_client():
    try:
        return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
    except Exception as e:
        pytest.skip(f"IPFS daemon not running: {e}")

# Initialize group signature
@pytest.fixture
def hospital_group():
    g = group("cpy06")()
    g.setup()
    return g

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
def hospital():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return GroupManager(private_key=private_key, public_key=public_key)

def test_storing_workflow(ipfs_client, hospital_group, doctor_key, patient, hospital):
    """Test the storing workflow"""
    doctor_key, gm = doctor_key
    
    # Step 1: Doctor creates record and signs it
    merkle_service = MerkleService()
    merkle_root, proofs = merkle_service.create_merkle_tree(TEST_RECORD)
    
    # Step 2: Sign with group signature
    signature_data = gm.sign(merkle_root, doctor_key)
    signature = signature_data["signature"]
    
    # Verify signature
    assert gm.verify(merkle_root, signature)
    
    # Step 3: Patient encrypts record
    key_patient = patient.generate_key()
    encrypted_record = patient.encrypt_record(TEST_RECORD, key_patient)
    
    # Step 4: Upload to IPFS
    cid = ipfs_client.add_bytes(encrypted_record)["Hash"]
    
    # Simulate blockchain transaction
    print(f"Record stored with CID: {cid}, Merkle Root: {merkle_root}")
    
    # Return data for next tests
    return {
        "cid": cid,
        "merkle_root": merkle_root,
        "signature": signature,
        "key_patient": key_patient,
        "encrypted_record": encrypted_record
    }

def test_sharing_workflow(ipfs_client, patient, doctor, test_storing_workflow):
    """Test the sharing workflow"""
    # Get data from storing workflow
    data = test_storing_workflow
    
    # Step 1: Patient retrieves and decrypts record
    # (In a real scenario, we would fetch from IPFS using the CID)
    
    # Step 2: Generate temporary key
    key_temp = os.urandom(32)
    
    # Step 3: Re-encrypt record with temporary key
    re_encrypted_record = patient.encrypt_record(TEST_RECORD, key_temp)
    
    # Step 4: Upload re-encrypted record to IPFS
    cid_share = ipfs_client.add_bytes(re_encrypted_record)["Hash"]
    
    # Step 5: Encrypt temporary key with doctor's public key
    encrypted_key = doctor.public_key.encrypt(
        key_temp,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    
    # Simulate sending to doctor
    print(f"Record shared with CID: {cid_share}")
    
    # Return data for next tests
    return {
        "cid_share": cid_share,
        "encrypted_key": encrypted_key,
        "key_temp": key_temp
    }

def test_purchasing_workflow(ipfs_client, patient, hospital, test_storing_workflow):
    """Test the purchasing workflow"""
    # Get data from storing workflow
    data = test_storing_workflow
    
    # Step 1: Buyer requests data with template hash and escrow
    template_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    escrow_amount = 1000000000000000000  # 1 ETH in wei
    
    # Simulate blockchain transaction
    request_id = 1
    
    # Step 2: Hospital matches patients
    # (In a real scenario, the hospital would find patients matching the template)
    
    # Step 3: Patient creates template with requested fields
    template_data = {
        "patientID": TEST_RECORD["patientID"],
        "diagnosis": TEST_RECORD["diagnosis"]
    }
    
    # Step 4: Patient encrypts template
    key_template = os.urandom(32)
    encrypted_template = patient.encrypt_record(template_data, key_template)
    
    # Step 5: Upload encrypted template to IPFS
    cid_template = ipfs_client.add_bytes(encrypted_template)["Hash"]
    
    # Step 6: Hospital submits reply
    # Simulate blockchain transaction
    
    # Step 7: Buyer verifies and finalizes
    # Simulate blockchain transaction
    
    print(f"Purchase completed with template CID: {cid_template}")
    
    return {
        "request_id": request_id,
        "template_hash": template_hash,
        "cid_template": cid_template
    }

def test_full_happy_path(ipfs_client, hospital_group, doctor_key, patient, doctor, hospital):
    """Test the full happy path"""
    # Run all workflows in sequence
    storing_data = test_storing_workflow(ipfs_client, hospital_group, doctor_key, patient, hospital)
    sharing_data = test_sharing_workflow(ipfs_client, patient, doctor, storing_data)
    purchasing_data = test_purchasing_workflow(ipfs_client, patient, hospital, storing_data)
    
    # Assert all workflows completed successfully
    assert storing_data["cid"] is not None
    assert sharing_data["cid_share"] is not None
    assert purchasing_data["cid_template"] is not None
    
    print("All workflows completed successfully!")
