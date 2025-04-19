import json
import os
import ipfshttpclient
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from web3 import Web3
import logging

# Import CPY06 group signature classes (adjust path as needed)
from pygroupsig import group, key

class Doctor:
    def __init__(self, member_key: MemberKey, group: 'Group', private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey,):
        self.member_key = member_key  
        self.group = group
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key

    def create_record(self, patient_id: str, diagnosis: str, notes: str) -> tuple[dict, str, str]:
        """Create a medical record and sign ID_Rec with CPY06 group signature."""
        record = {
            "patientID": patient_id,
            "date": "2025-04-18",
            "diagnosis": diagnosis,
            "doctorID": "DOC789",  # Anonymous in signature
            "notes": notes
        }
        # Compute Merkle root (simplified as SHA-256)
        return record
    
    def sign_record(self, record: dict) -> tuple[str, str]:
        """Sign the record with CPY06 group signature."""
        # Serialize and hash the record
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(json.dumps(record, sort_keys=True).encode())
        id_rec = digest.finalize().hex()
        # Sign with group signature
        sd = self.group.sign(id_rec, self.member_key)
        return id_rec, sd

    def access_record(self, patient_address: str, record_index: int, one_time_key: bytes) -> dict:
        """Access a record with a one-time key (decrypt and verify)."""
        try:
            # Query smart contract for record
            cid, sd, eid = self.contract.functions.getRecord(patient_address, record_index).call()
            with ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http') as client:
                record_content = client.cat(cid)
                # Decrypt with one-time key (AES-CTR)
                nonce = record_content[:16]
                ciphertext = record_content[16:]
                cipher = Cipher(algorithms.AES(one_time_key), modes.CTR(nonce), backend=default_backend())
                decryptor = cipher.decryptor()
                record_bytes = decryptor.update(ciphertext) + decryptor.finalize()
                record = json.loads(record_bytes.decode())
                # Verify signature
                digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
                digest.update(json.dumps(record, sort_keys=True).encode())
                id_rec = digest.finalize().hex()
                verify_result = self.group.verify(id_rec, sd)
                if verify_result["status"] != "success":
                    self.logger.warning(f"Invalid signature for CID {cid}")
                    raise ValueError("Invalid signature")
                return record
        except Exception as e:
            self.logger.error(f"Failed to access record: {e}")
            raise

class Patient:
    def __init__(self, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey, address: str, web3_provider: str, contract_address: str, contract_abi: list):
        self.private_key = private_key  # For PCS encryption/decryption
        self.public_key = public_key
        self.address = address  # Blockchain address
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        self.logger = logging.getLogger(__name__)

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

    def decrypt_hospital_info(self, eid: bytes) -> tuple[str, bytes]:
        """Decrypt hospital info and key."""
        plaintext = self.private_key.decrypt(
            eid,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        hospital_info = plaintext.decode()[:-64]  # Last 64 chars are key hex
        key_hex = plaintext.decode()[-64:]
        key = bytes.fromhex(key_hex)
        return hospital_info, key

    def store_record(self, record: dict, id_rec: str, sd: str, hospital_info: str) -> dict:
        """Encrypt, upload to IPFS MFS, and store metadata in blockchain."""
        try:
            # Encrypt record and hospital info
            key = os.urandom(32)  # K_Patient
            erec = self.encrypt_record(record, key)
            eid = self.encrypt_hospital_info(hospital_info, key)

            # Upload to IPFS MFS
            with ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http') as client:
                mfs_path = f"/patient{self.address}"
                client.files.mkdir(f"{mfs_path}/records", parents=True)
                record_cid = client.add_bytes(erec)["Hash"]
                client.files.write(f"{mfs_path}/records/record_{id_rec}.enc", f"/ipfs/{record_cid}", create=True)

            # Submit to blockchain smart contract
            tx_hash = self.contract.functions.addRecord(
                self.address,
                record_cid,
                sd,
                eid.hex()
            ).transact({'from': self.w3.eth.default_account})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return {
                "txId": receipt.transactionHash.hex(),
                "recordCid": record_cid,
                "certificate": {"signedMerkleRoot": sd, "encryptedHospitalInfoAndKey": eid.hex()},
                "patientAddress": self.address,
                "smartContractAddress": self.contract.address
            }
        except Exception as e:
            self.logger.error(f"Failed to store record: {e}")
            raise

    def access_records(self, group: 'Group') -> list[dict]:
        """Retrieve and decrypt records from blockchain and IPFS."""
        try:
            records = self.contract.functions.getRecords(self.address).call()
            decrypted_records = []
            with ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http') as client:
                for record_data in records:
                    cid, sd, eid_hex, _ = record_data
                    eid = bytes.fromhex(eid_hex)
                    # Decrypt hospital info and key
                    _, key = self.decrypt_hospital_info(eid)
                    # Fetch and decrypt record
                    record_content = client.cat(cid)
                    nonce = record_content[:16]
                    ciphertext = record_content[16:]
                    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
                    decryptor = cipher.decryptor()
                    record_bytes = decryptor.update(ciphertext) + decryptor.finalize()
                    record = json.loads(record_bytes.decode())
                    # Verify signature
                    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
                    digest.update(json.dumps(record, sort_keys=True).encode())
                    id_rec = digest.finalize().hex()
                    verify_result = group.verify(id_rec, sd)
                    if verify_result["status"] == "success":
                        decrypted_records.append(record)
                    else:
                        self.logger.warning(f"Invalid signature for CID {cid}")
            return decrypted_records
        except Exception as e:
            self.logger.error(f"Failed to retrieve records: {e}")
            raise

class GroupManager(Group):
    """Extends CPY06 Group to manage doctor membership and signature tracing."""
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setup()  # Initialize GroupKey, ManagerKey, etc.

    def add_doctor(self, member_key: MemberKey) -> None:
        """Simulate doctor join process (in practice, use join_mgr/join_mem)."""
        msg1 = self.join_mgr()
        msg2 = self.join_mem(msg1, member_key)
        msg3 = self.join_mgr(msg2)
        result = self.join_mem(msg3, member_key)
        if result["status"] != "success":
            self.logger.error("Doctor join failed")
            raise ValueError("Doctor join failed")

    def trace_signature(self, signature: str, revocation_manager: 'RevocationManager') -> str:
        """Trace a signature to identify the signer."""
        partial_g = self.open(signature, group_manager_partial=None)
        partial_r = revocation_manager.open(signature, revocation_manager_partial=None)
        result = self.open(
            signature,
            group_manager_partial=partial_g["partial_g"],
            revocation_manager_partial=partial_r["partial_r"]
        )
        if result["status"] == "success":
            return result["id"]
        self.logger.error("Signature tracing failed")
        raise ValueError("Signature tracing failed")

class RevocationManager:
    def __init__(self, revocation_key: RevocationManagerKey):
        self.revocation_key = revocation_key  # xi1, xi2 shares
        self.logger = logging.getLogger(__name__)

    def open(self, signature: str, revocation_manager_partial=None) -> dict:
        """Perform partial signature opening."""
        group = Group()  # Temporary group for open method
        group.revocation_manager_key = self.revocation_key
        return group.open(signature, revocation_manager_partial=revocation_manager_partial)

    def revoke_doctor(self, member_id: str, group_manager: GroupManager) -> None:
        """Revoke a doctor by adding to CRL."""
        result = group_manager.reveal(member_id)
        if result["status"] != "success":
            self.logger.error("Doctor revocation failed")
            raise ValueError("Doctor revocation failed")