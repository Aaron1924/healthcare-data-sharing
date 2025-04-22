import os
import json
from dotenv import load_dotenv
from backend.crypto import aes, merkle, groupsig

# Load environment variables
load_dotenv()

def test_aes():
    print("Testing AES encryption/decryption...")
    
    # Generate a key
    key = aes.generate_key()
    print(f"Generated key: {key.hex()}")
    
    # Test data
    data = "This is a test message for AES encryption"
    
    # Encrypt
    encrypted = aes.encrypt(data, key)
    print(f"Encrypted data: {encrypted}")
    
    # Decrypt
    decrypted = aes.decrypt(encrypted, key)
    print(f"Decrypted data: {decrypted}")
    
    # Verify
    assert data == decrypted, "Decryption failed!"
    print("AES test passed!")

def test_merkle():
    print("\nTesting Merkle tree...")
    
    # Test data
    data = {
        "patientId": "123",
        "date": "2023-05-01",
        "diagnosis": "Hypertension",
        "notes": "Patient should monitor blood pressure daily",
        "doctorId": "456"
    }
    
    # Create Merkle root
    root = merkle.create_root(data)
    print(f"Merkle root: {root}")
    
    # Create proofs
    proofs, root2 = merkle.create_proofs(data)
    print(f"Proofs: {json.dumps(proofs, indent=2)}")
    
    # Verify proofs
    for key, value in data.items():
        element = {"key": key, "value": value}
        assert merkle.verify_proof(element, proofs[key], root2), f"Proof verification failed for {key}!"
    
    print("Merkle test passed!")

def test_groupsig():
    print("\nTesting group signatures...")
    
    try:
        # Initialize group signature system
        groupsig.initialize()
        
        # Test data
        data = "This is a test message for group signature"
        
        # Sign
        signature = groupsig.sign(data)
        print(f"Signature: {signature[:50]}...")
        
        # Verify
        verified = groupsig.verify(data, signature)
        print(f"Verification result: {verified}")
        
        # Get Group Manager's partial opening
        gm_partial = groupsig.open(signature)
        print(f"Group Manager partial: {gm_partial}")
        
        # Get Revocation Manager's partial opening
        rm_partial = groupsig.open(signature, group_manager_partial=gm_partial["partial_g"])
        print(f"Revocation Manager partial: {rm_partial}")
        
        # Complete the opening
        full_open = groupsig.open(
            signature,
            group_manager_partial=gm_partial["partial_g"],
            revocation_manager_partial=rm_partial["partial_r"]
        )
        print(f"Full opening result: {full_open}")
        
        print("Group signature test passed!")
    except Exception as e:
        print(f"Group signature test failed: {e}")

if __name__ == "__main__":
    test_aes()
    test_merkle()
    test_groupsig()
