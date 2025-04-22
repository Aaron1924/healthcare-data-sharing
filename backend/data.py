import json
import os
import ipfshttpclient
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from typing import List, Dict, Optional, Tuple
from merkletools import MerkleTools
import json
import base64

from pygroupsig import group,key



class MerkleService:
    def __init__(self):
        self.mt = MerkleTools(hash_type="sha256")

    def create_merkle_tree(self, data: Dict) -> Tuple[str, Dict]:
        """
        Create a Merkle tree from a dictionary of data
        Returns: (root_hash, proofs)
        """
        # Convert dictionary to list of key-value pairs
        items = []
        for key, value in data.items():
            item = f"{key}:{value}"
            items.append(item)

        # Add items to Merkle tree
        self.mt.add_leaf(items, True)
        self.mt.make_tree()

        # Get root hash
        root_hash = self.mt.get_merkle_root()

        # Generate proofs for each item
        proofs = {}
        for i, item in enumerate(items):
            proof = self.mt.get_proof(i)
            proofs[item] = proof

        return root_hash, proofs

    def verify_proof(self, item: str, proof: List[Dict], root_hash: str) -> bool:
        """
        Verify a Merkle proof against a root hash
        """
        return self.mt.validate_proof(proof, item, root_hash)

    def get_proof_for_field(self, data: Dict, field: str) -> Optional[Dict]:
        """
        Get Merkle proof for a specific field in the data
        """
        if field not in data:
            return None

        item = f"{field}:{data[field]}"
        items = [f"{k}:{v}" for k, v in data.items()]

        self.mt.reset_tree()
        self.mt.add_leaf(items, True)
        self.mt.make_tree()

        try:
            index = items.index(item)
            return self.mt.get_proof(index)
        except ValueError:
            return None

    def verify_field(self, field: str, value: str, proof: List[Dict], root_hash: str) -> bool:
        """
        Verify a specific field's value using its Merkle proof
        """
        item = f"{field}:{value}"
        return self.verify_proof(item, proof, root_hash)

# def create_record():
#     record = {
#         "patientID": "12345",
#         "date": "2025-04-18",
#         "diagnosis": "Hypertension",
#         "doctorID": "DOC789",
#         "notes": "Patient advised to monitor blood pressure daily."
#     }


# Encrypt hospital info and key using PCS (simulated public-key encryption)
def encrypt_hospital_info_and_key(hospital_info_and_key):
    """Encrypt hospital info and patient key using PCS (simulated)

    In a real implementation, this would use a proper PCS scheme with the Group Manager's public key.
    For demo purposes, we'll use a simple encryption.

    Args:
        hospital_info_and_key: A string containing hospital info and patient key

    Returns:
        A base64-encoded string representing the encrypted data
    """
    # For demo purposes, we'll just base64 encode the data
    # In a real implementation, this would use proper encryption with the Group Manager's public key
    return base64.b64encode(hospital_info_and_key.encode()).decode()

def encrypt_record(record: dict, key: bytes) -> bytes:
    # Convert any bytes in the dictionary to base64 strings
    record_serializable = convert_bytes_to_base64(record)

    nonce = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    record_bytes = json.dumps(record_serializable).encode()
    erec = nonce + encryptor.update(record_bytes) + encryptor.finalize()
    return erec

def convert_bytes_to_base64(obj):
    """Convert bytes objects in nested dictionaries/lists to base64 strings."""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('ascii')
    elif isinstance(obj, dict):
        return {k: convert_bytes_to_base64(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_base64(i) for i in obj]
    else:
        return obj

def generate_private_key(random=True):
    if random:
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
    else:
        # Load from file or other source
        pass

def generate_public_key(private_key):
    return private_key.public_key()
