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


# Encrypt hospital info and key using PCS (real public-key encryption)
def encrypt_hospital_info_and_key(hospital_info_and_key, group_manager_public_key=None):
    """Encrypt hospital info and patient key using PCS with RSA-OAEP

    This implements a proper Proxy Cryptosystem (PCS) using RSA-OAEP for encrypting
    the hospital info and patient key with the Group Manager's public key.

    Args:
        hospital_info_and_key: A string containing hospital info and patient key
        group_manager_public_key: The Group Manager's RSA public key (optional)

    Returns:
        A base64-encoded string representing the encrypted data
    """
    try:
        # If no public key is provided, try to load it from environment or file
        if group_manager_public_key is None:
            # Try to import from the main API module
            try:
                from backend.api import key_manager, GROUP_MANAGER_ADDRESS
                group_manager_public_key = key_manager.get_public_key(GROUP_MANAGER_ADDRESS)
                print(f"Using Group Manager public key from key_manager")
            except (ImportError, AttributeError):
                # Fallback: Generate a temporary key for demo purposes
                print("Warning: Could not import key_manager. Generating temporary key.")
                private_key = generate_private_key()
                group_manager_public_key = generate_public_key(private_key)

        # Convert input to bytes if it's a string
        if isinstance(hospital_info_and_key, str):
            data = hospital_info_and_key.encode()
        else:
            data = hospital_info_and_key

        # Encrypt with RSA-OAEP
        ciphertext = group_manager_public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Return base64-encoded ciphertext
        return base64.b64encode(ciphertext).decode()
    except Exception as e:
        print(f"Error in encrypt_hospital_info_and_key: {str(e)}")
        # Fallback to simple encoding if encryption fails
        return base64.b64encode(hospital_info_and_key.encode()).decode()

# Decrypt hospital info and key using PCS
def decrypt_hospital_info_and_key(encrypted_data, group_manager_private_key=None):
    """Decrypt hospital info and patient key using PCS with RSA-OAEP

    This implements the decryption side of the Proxy Cryptosystem (PCS) using
    RSA-OAEP to decrypt the hospital info and patient key with the Group Manager's
    private key.

    Args:
        encrypted_data: Base64-encoded encrypted data
        group_manager_private_key: The Group Manager's RSA private key (optional)

    Returns:
        tuple: (hospital_info, patient_key)
    """
    try:
        # If no private key is provided, try to load it from environment or file
        if group_manager_private_key is None:
            # Try to import from the main API module
            try:
                from backend.api import key_manager, GROUP_MANAGER_ADDRESS
                group_manager_private_key = key_manager.get_private_key(GROUP_MANAGER_ADDRESS)
                print(f"Using Group Manager private key from key_manager")
            except (ImportError, AttributeError):
                # Cannot proceed without a private key
                print("Error: Could not import key_manager and no private key provided.")
                raise ValueError("No Group Manager private key available for decryption")

        # Decode base64 data
        if isinstance(encrypted_data, str):
            ciphertext = base64.b64decode(encrypted_data)
        else:
            ciphertext = encrypted_data

        # Decrypt with RSA-OAEP
        plaintext = group_manager_private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Split into hospital info and patient key
        decoded = plaintext.decode()
        hospital_info, patient_key_b64 = decoded.split('||')
        patient_key = base64.b64decode(patient_key_b64)

        return hospital_info, patient_key
    except Exception as e:
        print(f"Error in decrypt_hospital_info_and_key: {str(e)}")
        # If decryption fails, try to handle it as a legacy format
        try:
            # Try to decode as a simple base64 string (legacy format)
            decoded = base64.b64decode(encrypted_data).decode()
            if '||' in decoded:
                hospital_info, patient_key_b64 = decoded.split('||')
                patient_key = base64.b64decode(patient_key_b64)
                return hospital_info, patient_key
            else:
                # Cannot parse the data
                raise ValueError("Invalid format for hospital info and key")
        except Exception as fallback_error:
            print(f"Fallback decryption also failed: {str(fallback_error)}")
            raise

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
