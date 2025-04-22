import json
import os
import ipfshttpclient
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from backend.data import MerkleService
import logging
from typing import List, Dict, Optional, Tuple
from backend.data import encrypt_hospital_info_and_key,encrypt_record


class Patient:
    #blockchain_address: str
    def __init__(self, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey):
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key

    def encrypt_record(self, record: dict, key: bytes) -> bytes:
        """Encrypt record with K_Patient (AES-CTR)."""
        nonce = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        record_bytes = json.dumps(record).encode()
        erec = nonce + encryptor.update(record_bytes) + encryptor.finalize()
        return erec

    def encrypt_hospital_info(self, hospital_info: str, key: bytes) -> bytes:
        """Encrypt hospital info and key with PCS (RSA-OAEP)."""
        eid = self.public_key.encrypt(
            (hospital_info + key.hex()).encode(),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        return eid

    def generate_key(self) -> bytes:
        """Generate a random AES key for encryption."""
        return os.urandom(32)


    def upload_ipfs_records(self, ERecords: dict, HospitalInfo: str, GroupManagerPublicKey: rsa.RSAPublicKey, KeyERecord: bytes):
        try:
        # Connect to IPFS node
            client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')

            # Step 1: Create IPFS directory in MFS
            mfs_path = "/patient123"
            client.files.mkdir(f"{mfs_path}/records", parents=True)

            # Step 3: Encrypt record
            key = os.urandom(32)  # K_Patient (256-bit AES key)
            erec = encrypt_record(ERecords, key)

            # Step 4: Encrypt hospital info and key (PCS)
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
            public_key = private_key.public_key()
            eid = encrypt_hospital_info_and_key(HospitalInfo, KeyERecord, GroupManagerPublicKey)

            # Step 5: Upload encrypted record to MFS
            record_mfs_path = f"{mfs_path}/records/record1.enc"
            record_cid = client.add_bytes(erec)["Hash"]
            client.files.write(record_mfs_path, f"/ipfs/{record_cid}", create=True)
            print(f"Record CID: {record_cid}")

            # Step 6: Upload encrypted hospital info to MFS
            hospital_info_mfs_path = f"{mfs_path}/hospital_info.enc"
            hospital_info_cid = client.add_bytes(eid)["Hash"]
            client.files.write(hospital_info_mfs_path, f"/ipfs/{hospital_info_cid}", create=True)
            print(f"Hospital Info CID: {hospital_info_cid}")
        except Exception as e:
            print(f"Error: {e}")

class Doctor:
    #blockchain_address: str
    def __init__(self, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey):
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key


class GroupManager:
    def __init__(self, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey, group=None):
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key
        self.group = group  # The group signature group

    def provide_partial_opening(self, signature):
        """Provide partial opening information for a signature."""
        if self.group:
            result = self.group.open(signature)
            return result.get("partial_g")
        return None


class RevocationManager:
    def __init__(self, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey, group=None):
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key
        self.group = group  # The group signature group

    def provide_partial_opening(self, signature, group_manager_partial):
        """Provide partial opening information for a signature using the Group Manager's partial."""
        if self.group:
            result = self.group.open(signature, group_manager_partial=group_manager_partial)
            return result.get("partial_r")
        return None
