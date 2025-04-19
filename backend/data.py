import ipfshttpclient
from typing import Optional, Any, Dict, List, Tuple
import merkletools
from merkletools import MerkleTools
from hashlib import sha256
from pygroupsig import group, key
import json
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

class Record:
    def __init__(self,json_file_path,K_patient):
        self.data = {}
        self.ipfs_client = ipfshttpclient.connect()
        self.merkle_tree = MerkleTree()
    def encrypt_record(record, key):
        nonce = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        record_bytes = json.dumps(record).encode()
        erec = nonce + encryptor.update(record_bytes) + encryptor.finalize()
        return erec

class MerkleTree:
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
    


class IPFSClient:
    def __init__(self, ipfs_url,mfs_path):
        self.client = ipfshttpclient.connect(ipfs_url)
        self.directory = None
    
    def create_ipfs_directory(self, mfs_path):
        """
        Create a directory in IPFS
        """
        self.directory = mfs_path
        self.client.files.mkdir(mfs_path)
        print(f"Directory {mfs_path} created in IPFS.")

    def add_file(self,file_path):
        """
        Add a file to IPFS
        """
        if self.directory is None:
            raise ValueError("Directory not created. Call create_ipfs_directory first.")
        
        # Add file to IPFS
        res = self.client.add(file_path)
        file_hash = res['Hash']
        
        # Move file to the directory
        self.client.files.mv(f"/{file_hash}", f"{self.directory}/{os.path.basename(file_path)}")
        
        print(f"File {file_path} added to IPFS with hash {file_hash}.")
        return file_hash
    
    def retrive_file_dirc(self, file_hash):
        """
        Retrieve a file from IPFS
        """
        if self.directory is None:
            raise ValueError("Directory not created. Call create_ipfs_directory first.")
        
        # Retrieve file from IPFS
        res = self.client.cat(f"{self.directory}/{file_hash}")


class GroupSign:
    def __init__(self, group_name: str):
        self.group = group(group_name)()
        self.group.setup()
        self.group_key = self.group.group_key
        self.manager_key = self.group.manager_key
        self.revocation_manager_key = self.group.revocation_manager_key
    def join(self, gm: group, mk: key):
        """
        Join the group using the join protocol
        """
        msg2 = None
        seq = gm.join_seq()
        for _ in range(0, seq + 1, 2):
            msg1 = self.group.join_mgr(msg2)
        
            msg2 = gm.join_mem(msg1, mk)
        return