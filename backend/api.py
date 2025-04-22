import json
import os
import time
import hashlib
import base64
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Body, Response
from pydantic import BaseModel
import ipfshttpclient
from web3 import Web3
import uvicorn
from dotenv import load_dotenv
# Try to import Coinbase Cloud SDK, but make it optional
try:
    from cdp_sdk import CoinbaseCloud
    has_coinbase_sdk = True
except ImportError:
    has_coinbase_sdk = False
    print("Warning: cdp_sdk not found. Coinbase Cloud features will be disabled.")
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from backend.data import MerkleService, encrypt_record, encrypt_hospital_info_and_key
from backend.roles import Patient, Doctor, GroupManager
from backend.groupsig_utils import sign_message, verify_signature, open_signature_group_manager, open_signature_revocation_manager, open_signature_full

app = FastAPI(title="Healthcare Data Sharing API")

# Load environment variables
load_dotenv()

# Connect to local IPFS
IPFS_URL = os.getenv("IPFS_URL", "/ip4/127.0.0.1/tcp/5001")

# Try multiple IPFS connection URLs in case one fails
ipfs_urls = [
    IPFS_URL,
    "/ip4/127.0.0.1/tcp/5001",
    "/ip4/localhost/tcp/5001"
]

ipfs_client = None
for url in ipfs_urls:
    try:
        ipfs_client = ipfshttpclient.connect(url)
        print(f"Successfully connected to IPFS at {url}")
        break
    except Exception as e:
        print(f"Warning: Could not connect to IPFS at {url}: {e}")

# Function to check if IPFS is connected and working
def check_ipfs_connection():
    """Check if IPFS is connected and working"""
    global ipfs_client

    if ipfs_client is None:
        print("Warning: No IPFS client available.")
        return False

    try:
        # Try to get IPFS node ID as a simple check
        node_id = ipfs_client.id()
        print(f"IPFS node ID: {node_id.get('ID', 'unknown')}")
        return True
    except Exception as e:
        print(f"Warning: IPFS connection check failed: {str(e)}")
        # Try to reconnect
        for url in ipfs_urls:
            try:
                ipfs_client = ipfshttpclient.connect(url)
                print(f"Successfully reconnected to IPFS at {url}")
                return True
            except Exception as reconnect_error:
                print(f"Warning: Could not reconnect to IPFS at {url}: {reconnect_error}")

        # If all reconnection attempts fail
        ipfs_client = None
        print("Warning: Could not connect to any IPFS node. Storage functionality will be limited.")
        return False

if ipfs_client is None:
    print("Warning: Could not connect to any IPFS node. Storage functionality will be limited.")

# Connect to Base Sepolia testnet via Coinbase Cloud
BASE_SEPOLIA_RPC_URL = os.getenv("BASE_SEPOLIA_RPC_URL", "https://api.developer.coinbase.com/rpc/v1/base-sepolia/TU79b5nxSoHEPVmNhElKsyBqt9CUbNTf")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e")
# Default addresses for each role
PATIENT_ADDRESS = os.getenv("PATIENT_ADDRESS", "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A")
DOCTOR_ADDRESS = os.getenv("DOCTOR_ADDRESS", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
HOSPITAL_ADDRESS = os.getenv("HOSPITAL_ADDRESS", "0x28B317594b44483D24EE8AdCb13A1b148497C6ba")
BUYER_ADDRESS = os.getenv("BUYER_ADDRESS", "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce")
GROUP_MANAGER_ADDRESS = os.getenv("GROUP_MANAGER_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
REVOCATION_MANAGER_ADDRESS = os.getenv("REVOCATION_MANAGER_ADDRESS", "0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46")

# Default wallet address (for backward compatibility)
WALLET_ADDRESS = PATIENT_ADDRESS

# Generate RSA key pairs for testing
def generate_rsa_key_pair():
    """Generate an RSA key pair for testing"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Generate key pairs for each role (for testing only)
# In a real implementation, these would be stored securely
patient_private_key, patient_public_key = generate_rsa_key_pair()
doctor_private_key, doctor_public_key = generate_rsa_key_pair()

# Function to encrypt with RSA public key
def encrypt_with_public_key(data, public_key):
    """Encrypt data with an RSA public key"""
    if isinstance(data, str):
        data = data.encode()
    elif not isinstance(data, bytes):
        raise ValueError(f"Data must be bytes or string, got {type(data)}")

    ciphertext = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

# Function to decrypt with RSA private key
def decrypt_with_private_key(ciphertext, private_key):
    """Decrypt data with an RSA private key"""
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext

# Initialize Coinbase Cloud SDK (optional, for additional CDP features)
if has_coinbase_sdk:
    try:
        coinbase_cloud = CoinbaseCloud(
            project_id=os.getenv("COINBASE_PROJECT_ID", "05614f86-3dbd-45d9-be9d-69ceeb939336"),
            api_key_id=os.getenv("COINBASE_API_KEY_ID", "e89240c9-3a16-4777-896c-e702a70ff34a"),
            api_key_secret=os.getenv("COINBASE_API_KEY_SECRET", "Id9CXHM6392XOICcgrSx2YYdZdT6WqysI6cVh1PoDMq5dp5cx01woBsa9Y4xq3s2fHGNuwmZn9PiVJLlg96WDQ==")
        )
        print("Connected to Coinbase Cloud SDK")
    except Exception as e:
        print(f"Warning: Could not initialize Coinbase Cloud SDK: {e}")
        print("Some Coinbase Cloud features may be unavailable")
        coinbase_cloud = None
else:
    coinbase_cloud = None
    print("Coinbase Cloud SDK not available. Using direct RPC connection.")

# Connect to Web3 using the RPC URL
w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC_URL))

# Load contract ABI
try:
    with open("artifacts/contracts/DataHub.sol/DataHub.json", "r") as f:
        contract_json = json.load(f)
        contract_abi = contract_json["abi"]
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    print("Warning: Contract ABI not found or invalid. Using empty ABI.")
    contract_abi = []

contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# Function to clean CIDs (remove whitespace, etc.)
def clean_cid(cid):
    """Clean a CID by removing whitespace and other invalid characters"""
    if cid is None:
        return None
    # Remove leading/trailing whitespace
    cleaned = cid.strip()
    print(f"Cleaned CID: '{cid}' -> '{cleaned}'")
    return cleaned

# Function to handle IPFS operations with fallback
def store_on_ipfs(data):
    """Store data on IPFS with fallback to local storage

    Args:
        data: The data to store (bytes)

    Returns:
        str: The CID (Content Identifier) or local hash
    """
    # Check if IPFS is connected
    if check_ipfs_connection():
        try:
            # Store on IPFS
            print(f"Storing {len(data)} bytes on IPFS...")
            result = ipfs_client.add_bytes(data)
            print(f"IPFS add_bytes result: {result}")

            # Handle different return types
            if isinstance(result, dict) and "Hash" in result:
                cid = result["Hash"]
                print(f"Successfully stored on IPFS with CID: {cid}")
                return cid
            elif isinstance(result, str):
                print(f"Successfully stored on IPFS with CID: {result}")
                return result
            else:
                print(f"Warning: Unexpected IPFS result format: {result}")
                # Fall back to local storage
        except Exception as e:
            print(f"Warning: Error storing on IPFS: {str(e)}")
            # Fall back to local storage
    else:
        print("IPFS not connected, using local storage")

    # Fallback: Store locally (for development only)
    import hashlib
    file_hash = hashlib.sha256(data).hexdigest()
    os.makedirs("local_storage", exist_ok=True)
    with open(f"local_storage/{file_hash}", "wb") as f:
        f.write(data)
    print(f"Stored file locally with hash: {file_hash}")
    return file_hash

# Function to encrypt a record
def encrypt_record(data, key):
    """
    Encrypt a record using AES-CTR

    Args:
        data: The data to encrypt (bytes, string, or dict)
        key: The encryption key (bytes)

    Returns:
        bytes: The encrypted data (nonce + ciphertext)
    """
    # Convert dict to JSON string if needed
    if isinstance(data, dict):
        data = json.dumps(data).encode()
    # Convert string to bytes if needed
    elif isinstance(data, str):
        data = data.encode()
    # Ensure data is bytes
    elif not isinstance(data, bytes):
        raise ValueError(f"Data must be bytes, string, or dict, got {type(data)}")

    # Generate a random nonce
    nonce = os.urandom(16)

    # Create a cipher object
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()

    # Encrypt the data
    ciphertext = encryptor.update(data) + encryptor.finalize()

    # Return the nonce + ciphertext
    return nonce + ciphertext

# Function to decrypt a record
def decrypt_record(encrypted_data, key):
    """
    Decrypt a record using AES-CTR

    Args:
        encrypted_data: The encrypted data (nonce + ciphertext)
        key: The decryption key (bytes)

    Returns:
        dict: The decrypted record as a dictionary
    """
    try:
        # First 16 bytes are the nonce
        nonce = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        # Create a cipher object
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt the data
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Parse the JSON
        try:
            return json.loads(decrypted_data.decode())
        except json.JSONDecodeError as e:
            # If JSON decoding fails, try to return the raw data as a string
            print(f"Warning: JSON decoding failed: {str(e)}")
            print(f"Decrypted data (first 100 bytes): {decrypted_data[:100]}")
            return {"raw_data": decrypted_data.decode(errors='replace')}
    except Exception as e:
        print(f"Error decrypting record: {str(e)}")
        raise

# Models
class RecordData(BaseModel):
    patientID: str
    date: str
    diagnosis: str
    doctorID: str
    notes: str

class ShareRequest(BaseModel):
    record_cid: str
    doctor_address: str

class PurchaseRequest(BaseModel):
    template_hash: str
    amount: float

# API Endpoints
@app.post("/api/records/sign")
async def sign_record(record_data: dict):
    """
    Doctor creates and signs a record, which is then returned to be encrypted and stored
    """
    try:
        # Create Merkle tree from record data
        merkle_service = MerkleService()
        merkle_root, proofs = merkle_service.create_merkle_tree(record_data)

        # Sign the merkle root with group signature using the doctor's member key
        signature = sign_message(merkle_root)

        # If group signature fails, fall back to a mock signature
        if signature is None:
            print("Warning: Group signature failed. Using mock signature.")
            signature = hashlib.sha256(f"{merkle_root}_{int(time.time())}".encode()).hexdigest()

        return {
            "record": record_data,
            "merkleRoot": merkle_root,
            "proofs": proofs,
            "signature": signature
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/records/store")
async def store_record(data: dict):
    """
    Store an encrypted record on IPFS and register it on the blockchain
    """
    try:
        # Extract data
        record = data.get("record", {})
        signature = data.get("signature", "")
        merkle_root = data.get("merkleRoot", "")
        patient_address = data.get("patientAddress", "")
        hospital_info = data.get("hospitalInfo", "General Hospital")

        # Log the received data for debugging
        print(f"Received record store request:")
        print(f"  Record type: {type(record)}")
        print(f"  Signature: {signature[:20]}...")
        print(f"  Merkle root: {merkle_root[:20]}...")
        print(f"  Patient address: {patient_address}")
        print(f"  Hospital info: {hospital_info}")

        # Validate inputs
        if not record or not signature or not merkle_root or not patient_address:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # In a real implementation, we would get the patient's public key from a key server
        # For demo purposes, we'll generate a key deterministically
        patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()
        print(f"Generated patient key: {patient_key[:5].hex()}...")

        try:
            # Encrypt the record with the patient's key
            record_json = json.dumps(record).encode()
            print(f"Record JSON length: {len(record_json)} bytes")
            encrypted_record = encrypt_record(record_json, patient_key)
            print(f"Encrypted record length: {len(encrypted_record)} bytes")

            # Store the encrypted record on IPFS
            cid = store_on_ipfs(encrypted_record)
            print(f"Stored on IPFS with CID: {cid}")

            # Generate eId = PCS(HospitalInfo||K_patient, PKgm)
            # In a real implementation, this would use a proper PCS scheme with the Group Manager's public key
            # For demo purposes, we'll use a simple encryption
            hospital_info_and_key = f"{hospital_info}||{base64.b64encode(patient_key).decode()}"
            print(f"Hospital info and key: {hospital_info_and_key[:20]}...")

            eId = encrypt_hospital_info_and_key(hospital_info_and_key)
            print(f"Generated eId: {eId[:20]}...")

            # In a real implementation, this would be encrypted with the Group Manager's public key
            # so that only the Group Manager can decrypt it

            # In a real implementation, we would register this on the blockchain
            # For demo purposes, we'll just return the CID and eId
            result = {
                "cid": cid,
                "merkleRoot": merkle_root,
                "eId": eId,
                "txHash": f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"
            }
            print(f"Returning result: {result}")
            return result
        except Exception as inner_e:
            print(f"Inner exception: {str(inner_e)}")
            print(f"Exception type: {type(inner_e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing record: {str(inner_e)}")
    except Exception as e:
        print(f"Outer exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/records/list")
@app.get("/api/records/list")
async def list_patient_records(patient_address: str):
    """
    List all records for a patient
    """
    try:
        # Check if the wallet address matches the Patient address
        if patient_address == PATIENT_ADDRESS:
            print(f"Patient {patient_address} is listing their records")
        else:
            print(f"Warning: Non-patient address {patient_address} is attempting to list records")

        # In a real implementation, we would query the blockchain for all records owned by this patient
        # For demo purposes, we'll check the local storage directory
        records = []

        # Check if we have a local storage directory
        if os.path.exists("local_storage"):
            # List all files in the directory
            for filename in os.listdir("local_storage"):
                file_path = os.path.join("local_storage", filename)
                if os.path.isfile(file_path):
                    try:
                        # Try to decrypt the record
                        with open(file_path, "rb") as f:
                            encrypted_record = f.read()

                        # Generate the patient's key deterministically
                        patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()

                        # Decrypt the record
                        decrypted_record = decrypt_record(encrypted_record, patient_key)

                        # Add the record to the list if it belongs to this patient
                        # Check both patientId and patientID (case sensitivity)
                        patient_id = decrypted_record.get("patientId") or decrypted_record.get("patientID")

                        # Print debug info
                        print(f"Found record with patient ID: {patient_id}")
                        print(f"Looking for patient address: {patient_address}")

                        if patient_id == patient_address:
                            # Add metadata to the record
                            decrypted_record["cid"] = filename
                            decrypted_record["timestamp"] = os.path.getmtime(file_path)
                            records.append(decrypted_record)
                            print(f"Added record {filename} to patient's records")
                    except Exception as e:
                        # Skip records that can't be decrypted with this patient's key
                        print(f"Skipping record {filename}: {str(e)}")

        # If we have IPFS, we can also check there
        if ipfs_client:
            try:
                # In a real implementation, we would query IPFS for records owned by this patient
                # For demo purposes, we'll check the pinned items
                pins = ipfs_client.pin.ls()
                if 'Keys' in pins:
                    for pin_cid in pins['Keys']:
                        if pin_cid not in [r.get('cid') for r in records]:  # Skip if already added
                            try:
                                # Try to retrieve and decrypt the record
                                encrypted_record = ipfs_client.cat(pin_cid)

                                # Generate the patient's key deterministically
                                patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()

                                # Decrypt the record
                                decrypted_record = decrypt_record(encrypted_record, patient_key)

                                # Check both patientId and patientID (case sensitivity)
                                patient_id = decrypted_record.get("patientId") or decrypted_record.get("patientID")

                                # Print debug info
                                print(f"IPFS: Found record with patient ID: {patient_id}")

                                if patient_id == patient_address:
                                    # Add metadata to the record
                                    decrypted_record["cid"] = pin_cid
                                    decrypted_record["timestamp"] = int(time.time())  # Use current time as fallback
                                    records.append(decrypted_record)
                                    print(f"IPFS: Added record {pin_cid} to patient's records")
                            except Exception as e:
                                # Skip records that can't be decrypted with this patient's key
                                print(f"IPFS: Skipping record {pin_cid}: {str(e)}")
            except Exception as e:
                print(f"Error checking IPFS pins: {str(e)}")

        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/records/retrieve")
async def retrieve_record(data: dict):
    """
    Patient retrieves and decrypts a record using their key
    """
    try:
        # Extract data
        cid = data.get("cid", "")
        merkle_root = data.get("merkleRoot", "")
        signature = data.get("signature", "")
        eId = data.get("eId", "")
        patient_address = data.get("patientAddress", "")

        # Validate inputs
        if not cid or not patient_address or not eId:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Check if the wallet address matches the Patient address
        if patient_address == PATIENT_ADDRESS:
            print(f"Patient {patient_address} is retrieving a record")
        else:
            print(f"Warning: Non-patient address {patient_address} is attempting to retrieve a record")

        # Retrieve the encrypted record from IPFS
        if ipfs_client:
            try:
                encrypted_record = ipfs_client.cat(cid)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Error retrieving record from IPFS: {str(e)}")
        else:
            # Fallback for development (local storage)
            try:
                with open(f"local_storage/{cid}", "rb") as f:
                    encrypted_record = f.read()
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Record not found in local storage")

        # In a real implementation, the patient would:
        # 1. Verify the signature on the IDrecord (merkle_root) using the group public key
        # 2. Decrypt the eId to get the hospital info and patient key

        # Verify the signature (in a real implementation, this would use the group public key)
        # For demo purposes, we'll just log that we received it
        print(f"Verifying signature: {signature[:20]}... on merkle_root: {merkle_root[:20]}...")

        # Decrypt the eId (in a real implementation, this would be decrypted by the patient)
        # For demo purposes, we'll just log that we received it
        print(f"Decrypting eId: {eId[:20]}...")

        # Generate the patient's key deterministically (for demo purposes)
        # In a real implementation, this would be extracted from the decrypted eId
        patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()

        # Decrypt the record
        try:
            decrypted_record = decrypt_record(encrypted_record, patient_key)
            return decrypted_record
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error decrypting record: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/store")
async def store_record(
    cid: str = Body(...),
    merkle_root: str = Body(...),
    signature: str = Body(...),
    wallet_address: str = Body(...)
):
    """
    Patient stores the record on IPFS and registers it on the blockchain
    """
    try:
        # Check if the wallet address matches the Patient address
        if wallet_address == PATIENT_ADDRESS:
            print(f"Patient {wallet_address} is storing record {cid} with merkle root {merkle_root}")
        else:
            print(f"Warning: Non-patient address {wallet_address} is attempting to store a record")

        # This would call the smart contract in production
        # tx_hash = contract.functions.storeData(cid, merkle_root, signature).transact({'from': wallet_address})
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "transaction_hash": "placeholder_tx_hash"  # Replace with actual tx hash
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/share")
@app.post("/share")
async def share_record(record_cid: str = Body(None), doctor_address: str = Body(None), wallet_address: str = Body(...), share_req: ShareRequest = None):
    """
    Patient shares a record with a doctor via IPFS (off-chain)
    """
    try:
        # Handle both parameter formats
        if share_req is None and record_cid is not None and doctor_address is not None:
            # Parameters were passed directly
            actual_record_cid = record_cid
            actual_doctor_address = doctor_address
            print(f"Using direct parameters: record_cid={record_cid}, doctor_address={doctor_address}")
        elif share_req is not None:
            # Parameters were passed as a ShareRequest object
            actual_record_cid = share_req.record_cid
            actual_doctor_address = share_req.doctor_address
            print(f"Using ShareRequest object: record_cid={actual_record_cid}, doctor_address={actual_doctor_address}")
        else:
            # Missing required parameters
            raise HTTPException(status_code=400, detail="Missing required parameters: record_cid and doctor_address")

        # Check if the wallet address matches the Patient address
        if wallet_address == PATIENT_ADDRESS:
            print(f"Patient {wallet_address} is sharing a record with doctor {actual_doctor_address}")
        else:
            print(f"Warning: Non-patient address {wallet_address} is attempting to share a record")

        # Check if the doctor address is valid
        if actual_doctor_address != DOCTOR_ADDRESS:
            print(f"Warning: Sharing with non-doctor address {actual_doctor_address}")

        # 1. Retrieve and decrypt the record
        try:
            # Check if IPFS is connected
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    print(f"Retrieving record {actual_record_cid} from IPFS...")
                    original_record = ipfs_client.cat(actual_record_cid)
                    print(f"Retrieved {len(original_record)} bytes from IPFS")
                except Exception as ipfs_error:
                    print(f"Error retrieving from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        print(f"Trying local storage for {actual_record_cid}...")
                        with open(f"local_storage/{actual_record_cid}", "rb") as f:
                            original_record = f.read()
                        print(f"Retrieved {len(original_record)} bytes from local storage")
                    except FileNotFoundError:
                        raise HTTPException(status_code=404, detail=f"Record not found in IPFS or local storage: {actual_record_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    print(f"IPFS not connected, trying local storage for {actual_record_cid}...")
                    with open(f"local_storage/{actual_record_cid}", "rb") as f:
                        original_record = f.read()
                    print(f"Retrieved {len(original_record)} bytes from local storage")
                except FileNotFoundError:
                    raise HTTPException(status_code=404, detail=f"Record not found in local storage and IPFS is not available")

            # In a real implementation, we would get the patient's key from secure storage
            # For demo purposes, we'll generate a key deterministically
            patient_key = hashlib.sha256(f"{wallet_address}_key".encode()).digest()
            print(f"Generated patient key: {patient_key[:5].hex()}...")

            # Decrypt the record
            try:
                decrypted_record = decrypt_record(original_record, patient_key)
                print(f"Successfully decrypted record: {decrypted_record}")
            except Exception as decrypt_error:
                print(f"Error decrypting record: {str(decrypt_error)}")
                raise HTTPException(status_code=500, detail=f"Error decrypting record: {str(decrypt_error)}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving or decrypting record: {str(e)}")

        # 2. Generate temporary key and re-encrypt
        # Generate a truly random key for better security
        temp_key = os.urandom(32)
        print(f"Generated random temp key: {temp_key[:5].hex()}...")
        print(f"Decrypted record type: {type(decrypted_record)}")
        print(f"Decrypted record: {decrypted_record}")
        try:
            re_encrypted_record = encrypt_record(decrypted_record, temp_key)
            print(f"Re-encrypted record length: {len(re_encrypted_record)} bytes")
        except Exception as enc_error:
            print(f"Error re-encrypting record: {str(enc_error)}")
            print(f"Error type: {type(enc_error)}")
            # Try to convert the record to a JSON string manually
            print("Attempting manual JSON conversion...")
            record_json = json.dumps(decrypted_record).encode()
            re_encrypted_record = encrypt_record(record_json, temp_key)

        # 3. Upload re-encrypted record to IPFS
        try:
            # Try to get the result as a dictionary with a "Hash" key
            add_result = ipfs_client.add_bytes(re_encrypted_record)
            print(f"IPFS add_bytes result: {add_result}")

            # Handle different return types
            if isinstance(add_result, dict) and "Hash" in add_result:
                cid_share = add_result["Hash"]
            elif isinstance(add_result, str):
                cid_share = add_result
            else:
                # Fallback to local storage
                print(f"Warning: Unexpected IPFS result format: {add_result}")
                cid_share = store_on_ipfs(re_encrypted_record)
        except Exception as ipfs_error:
            print(f"Error uploading to IPFS: {str(ipfs_error)}")
            # Fallback to local storage
            cid_share = store_on_ipfs(re_encrypted_record)

        # 4. Get doctor's public key (in a real implementation, this would be retrieved from a directory)
        # For demo purposes, we'll use our pre-generated doctor's public key
        print(f"Using doctor's public key for encryption")

        # 5. Encrypt temporary key with doctor's public key
        try:
            # Use our encrypt_with_public_key function
            encrypted_key = encrypt_with_public_key(temp_key, doctor_public_key)
            print(f"Successfully encrypted temp key: {len(encrypted_key)} bytes")
        except Exception as encrypt_error:
            print(f"Error encrypting with doctor's public key: {str(encrypt_error)}")
            # Fallback to direct encryption
            encrypted_key = doctor_public_key.encrypt(
                temp_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            print(f"Used fallback encryption method: {len(encrypted_key)} bytes")

        # 6. Create sharing metadata
        current_time = int(time.time())
        sharing_metadata = {
            "patient_address": wallet_address,
            "doctor_address": actual_doctor_address,
            "record_cid": cid_share,
            "original_cid": actual_record_cid,  # Include the original CID for key generation
            "encrypted_key": encrypted_key.hex(),
            "timestamp": current_time,
            "expiration": current_time + 30*24*60*60,  # 30 days
            # In a real implementation, this would be signed with the patient's private key
            "signature": f"mock_signature_for_{wallet_address}_{current_time}"
        }

        # 7. Upload sharing metadata to IPFS
        try:
            # Try to get the result as a dictionary with a "Hash" key
            add_json_result = ipfs_client.add_json(sharing_metadata)
            print(f"IPFS add_json result: {add_json_result}")

            # Handle different return types
            if isinstance(add_json_result, dict) and "Hash" in add_json_result:
                sharing_metadata_cid = add_json_result["Hash"]
            elif isinstance(add_json_result, str):
                sharing_metadata_cid = add_json_result
            else:
                # Fallback to local storage
                print(f"Warning: Unexpected IPFS result format: {add_json_result}")
                # Convert to bytes and store
                metadata_bytes = json.dumps(sharing_metadata).encode()
                sharing_metadata_cid = store_on_ipfs(metadata_bytes)
        except Exception as ipfs_error:
            print(f"Error uploading metadata to IPFS: {str(ipfs_error)}")
            # Fallback to local storage
            metadata_bytes = json.dumps(sharing_metadata).encode()
            sharing_metadata_cid = store_on_ipfs(metadata_bytes)

        # 8. Pin both files
        try:
            ipfs_client.pin.add(cid_share)
            print(f"Pinned record CID: {cid_share}")
        except Exception as pin_error:
            print(f"Warning: Error pinning record: {str(pin_error)}")

        try:
            ipfs_client.pin.add(sharing_metadata_cid)
            print(f"Pinned metadata CID: {sharing_metadata_cid}")
        except Exception as pin_error:
            print(f"Warning: Error pinning metadata: {str(pin_error)}")

        # 9. Notify the doctor (in a real implementation, this would send a notification)
        # For demo purposes, we'll just log it
        print(f"Notifying doctor {actual_doctor_address} about shared record {sharing_metadata_cid}")

        return {
            "status": "success",
            "sharing_metadata_cid": sharing_metadata_cid,
            "record_cid": cid_share
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/request")
async def request_purchase(purchase_req: PurchaseRequest, wallet_address: str = Body(...)):
    """
    Buyer requests to purchase data (on-chain)
    """
    try:
        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is requesting a purchase for template hash {purchase_req.template_hash} with amount {purchase_req.amount} ETH")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to request a purchase")

        # This would call the smart contract in production
        # tx_hash = contract.functions.request(purchase_req.template_hash).transact({
        #     'from': wallet_address,
        #     'value': w3.toWei(purchase_req.amount, 'ether')
        # })
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "request_id": "placeholder_request_id",
            "transaction_hash": "placeholder_tx_hash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/reply")
async def reply_to_purchase(
    request_id: str = Body(...),
    template_cid: str = Body(...),
    wallet_address: str = Body(...)
):
    """
    Hospital replies to a purchase request
    """
    try:
        # Check if the wallet address matches the Hospital address
        if wallet_address == HOSPITAL_ADDRESS:
            print(f"Hospital {wallet_address} is replying to purchase request {request_id} with template {template_cid}")
        else:
            print(f"Warning: Non-hospital address {wallet_address} is attempting to reply to a purchase request")

        # This would call the smart contract in production
        # tx_hash = contract.functions.reply(request_id, template_cid).transact({'from': wallet_address})
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "transaction_hash": "placeholder_tx_hash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/finalize")
async def finalize_purchase(
    request_id: str = Body(...),
    approved: bool = Body(...),
    recipients: List[str] = Body(...),
    wallet_address: str = Body(...)
):
    """
    Buyer finalizes a purchase
    """
    try:
        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is finalizing purchase request {request_id} with approval={approved} and {len(recipients)} recipients")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to finalize a purchase request")

        # This would call the smart contract in production
        # tx_hash = contract.functions.finalize(request_id, approved, recipients).transact({'from': wallet_address})
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "transaction_hash": "placeholder_tx_hash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/access_shared")
async def access_shared_record(metadata_cid: str = Body(...), wallet_address: str = Body(...)):
    """
    Doctor accesses a shared record via IPFS
    """
    try:
        # 1. Retrieve sharing metadata
        try:
            # Clean the metadata CID
            clean_metadata_cid = clean_cid(metadata_cid)
            print(f"Using cleaned metadata CID: {clean_metadata_cid}")

            # Check if IPFS is connected
            if check_ipfs_connection():
                try:
                    # Try to use cat and manual JSON parsing (more reliable than cat_json)
                    metadata_bytes = ipfs_client.cat(clean_metadata_cid)
                    sharing_metadata = json.loads(metadata_bytes.decode())
                    print(f"Retrieved sharing metadata from IPFS: {sharing_metadata}")
                except Exception as cat_error:
                    print(f"Error retrieving from IPFS: {str(cat_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{clean_metadata_cid}", "rb") as f:
                            metadata_bytes = f.read()
                        sharing_metadata = json.loads(metadata_bytes.decode())
                        print(f"Retrieved sharing metadata from local storage: {sharing_metadata}")
                    except Exception as local_error:
                        print(f"Error retrieving from local storage: {str(local_error)}")
                        raise Exception(f"Failed to retrieve metadata: {str(local_error)}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{clean_metadata_cid}", "rb") as f:
                        metadata_bytes = f.read()
                    sharing_metadata = json.loads(metadata_bytes.decode())
                    print(f"Retrieved sharing metadata from local storage: {sharing_metadata}")
                except Exception as local_error:
                    print(f"Error retrieving from local storage: {str(local_error)}")
                    raise Exception(f"Failed to retrieve metadata: {str(local_error)}")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error retrieving sharing metadata: {str(e)}")

        # Check if the wallet address matches the Doctor address
        if wallet_address == DOCTOR_ADDRESS:
            print(f"Doctor {wallet_address} is accessing a shared record")
        else:
            print(f"Warning: Non-doctor address {wallet_address} is attempting to access a shared record")

        # 2. Verify it's intended for this doctor
        if sharing_metadata["doctor_address"] != wallet_address:
            raise HTTPException(status_code=403, detail="Not authorized to access this record")

        # 3. Verify it hasn't expired
        current_time = int(time.time())
        if current_time > sharing_metadata.get("expiration", 0):
            raise HTTPException(status_code=403, detail="Sharing has expired")

        # 4. In a real implementation, we would verify the patient's signature
        # For demo purposes, we'll skip this step

        # 5. Retrieve the encrypted record from IPFS
        record_cid = sharing_metadata["record_cid"]
        clean_record_cid = clean_cid(record_cid)
        print(f"Using cleaned record CID: {clean_record_cid}")

        try:
            # Check if IPFS is connected
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    encrypted_record = ipfs_client.cat(clean_record_cid)
                    print(f"Retrieved encrypted record from IPFS: {len(encrypted_record)} bytes")
                except Exception as ipfs_error:
                    print(f"Error retrieving from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{clean_record_cid}", "rb") as f:
                            encrypted_record = f.read()
                        print(f"Retrieved encrypted record from local storage: {len(encrypted_record)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"Record not found in IPFS or local storage: {clean_record_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{clean_record_cid}", "rb") as f:
                        encrypted_record = f.read()
                    print(f"Retrieved encrypted record from local storage: {len(encrypted_record)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"Record not found in local storage and IPFS is not available")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error retrieving record: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving shared record: {str(e)}")

        # 6. In a real implementation, the doctor would decrypt the temporary key
        # using their private key. For demo purposes, we'll simulate this:
        try:
            encrypted_key_hex = sharing_metadata.get("encrypted_key", "")
            if encrypted_key_hex:
                encrypted_key = bytes.fromhex(encrypted_key_hex)
                print(f"Encrypted key length: {len(encrypted_key)} bytes")
            else:
                print("Warning: No encrypted key found in sharing metadata")

            # In a real implementation, the doctor would decrypt the temporary key using their private key
            # We'll actually do this here with our pre-generated doctor's private key
            try:
                # Try to decrypt the encrypted key with the doctor's private key
                if encrypted_key_hex:
                    try:
                        # Use our decrypt_with_private_key function
                        decrypted_key = decrypt_with_private_key(encrypted_key, doctor_private_key)
                        print(f"Successfully decrypted temp key with doctor's private key: {decrypted_key[:5].hex()}...")
                    except Exception as decrypt_error:
                        print(f"Error decrypting with doctor's private key: {str(decrypt_error)}")
                        # Fallback to direct decryption
                        decrypted_key = doctor_private_key.decrypt(
                            encrypted_key,
                            padding.OAEP(
                                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                algorithm=hashes.SHA256(),
                                label=None
                            )
                        )
                        print(f"Used fallback decryption method: {decrypted_key[:5].hex()}...")
                else:
                    # If no encrypted key is found, fall back to deterministic key generation
                    print("No encrypted key found, falling back to deterministic key generation")

                    # Get record CID and doctor address from metadata
                    record_cid = sharing_metadata["record_cid"]
                    doctor_address = sharing_metadata["doctor_address"]

                    # Get the original record CID from the sharing metadata if available
                    original_cid = sharing_metadata.get("original_cid", "unknown")

                    # Generate fallback keys
                    if original_cid != "unknown":
                        # If we have the original CID, use that
                        fallback_key1 = hashlib.sha256(f"shared_key_{original_cid}_{doctor_address}".encode()).digest()
                        print(f"Generated fallback key using original CID: {fallback_key1[:5].hex()}...")
                    else:
                        fallback_key1 = None

                    # Try with the record CID
                    fallback_key2 = hashlib.sha256(f"shared_key_{record_cid}_{doctor_address}".encode()).digest()
                    print(f"Generated fallback key using record CID: {fallback_key2[:5].hex()}...")

                    # Also try the old method
                    fallback_key3 = hashlib.sha256(f"temp_key_{metadata_cid}".encode()).digest()
                    print(f"Generated fallback key using metadata CID: {fallback_key3[:5].hex()}...")

                    # Use the first fallback key as the primary key
                    decrypted_key = fallback_key1 if fallback_key1 is not None else fallback_key2
            except Exception as e:
                print(f"Error processing encrypted key: {str(e)}")
                # Fall back to deterministic key generation as a last resort
                decrypted_key = hashlib.sha256(f"temp_key_{metadata_cid}".encode()).digest()
                print(f"Using last resort fallback key: {decrypted_key[:5].hex()}...")
        except Exception as e:
            print(f"Warning: Error processing encrypted key: {str(e)}")
            # Fallback to deterministic key generation
            decrypted_key = hashlib.sha256(f"temp_key_{metadata_cid}".encode()).digest()

        # 7. Decrypt the shared record
        try:
            # Print debug info
            print(f"Attempting to decrypt shared record with key: {decrypted_key[:5].hex()}...")
            print(f"Encrypted record length: {len(encrypted_record)} bytes")
            print(f"First 16 bytes (nonce): {encrypted_record[:16].hex()}")

            # Try multiple keys for decryption
            keys_to_try = [
                # First try the key generated using the doctor's private key
                decrypted_key
            ]

            # Add fallback keys if they exist
            if 'fallback_key1' in locals() and fallback_key1 is not None:
                keys_to_try.append(fallback_key1)
            if 'fallback_key2' in locals() and fallback_key2 is not None:
                keys_to_try.append(fallback_key2)
            if 'fallback_key3' in locals() and fallback_key3 is not None:
                keys_to_try.append(fallback_key3)

            # Finally try the old method
            keys_to_try.append(hashlib.sha256(f"temp_key_{metadata_cid}".encode()).digest())

            # Remove None values
            keys_to_try = [k for k in keys_to_try if k is not None]

            decryption_success = False
            for i, key in enumerate(keys_to_try):
                try:
                    print(f"Trying key {i+1}/{len(keys_to_try)}: {key[:5].hex()}...")
                    # Try to decrypt using our decrypt_record function
                    decrypted_record = decrypt_record(encrypted_record, key)
                    print(f"Successfully decrypted record with key {i+1}: {decrypted_record}")
                    decryption_success = True
                    break
                except Exception as decrypt_error:
                    print(f"Error using decrypt_record with key {i+1}: {str(decrypt_error)}")

                    # Try manual decryption as a fallback
                    try:
                        # First 16 bytes are the nonce
                        nonce = encrypted_record[:16]
                        ciphertext = encrypted_record[16:]

                        # Create a cipher object
                        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
                        decryptor = cipher.decryptor()

                        # Decrypt the data
                        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

                        # Try to parse as JSON with error handling for UTF-8 decoding
                        try:
                            # Try to decode as UTF-8 with error handling
                            decoded_str = decrypted_data.decode('utf-8', errors='replace')
                            print(f"Decoded string (first 100 chars): {decoded_str[:100]}")

                            # Try to parse as JSON
                            decrypted_record = json.loads(decoded_str)
                            print(f"Successfully parsed JSON manually with key {i+1}")
                            decryption_success = True
                            break
                        except json.JSONDecodeError as json_error:
                            print(f"JSON parsing error with key {i+1}: {str(json_error)}")
                            # Continue to the next key
                    except Exception as manual_error:
                        print(f"Manual decryption failed with key {i+1}: {str(manual_error)}")
                        # Continue to the next key

            # If all decryption attempts failed
            if not decryption_success:
                # Return a helpful error message
                decrypted_record = {
                    "error": "Could not decrypt record with any key",
                    "message": "This could be due to a key mismatch between sharing and accessing",
                    "metadata": {
                        "record_cid": record_cid,
                        "metadata_cid": metadata_cid,
                        "doctor_address": wallet_address,
                        "patient_address": sharing_metadata.get("patient_address", "unknown")
                    }
                }
                print("All decryption attempts failed. Returning error information.")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error during decryption: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error decrypting record: {str(e)}")

        # 8. Pin the record for future access
        if ipfs_client:
            ipfs_client.pin.add(record_cid)

        return {
            "status": "success",
            "record": decrypted_record,
            "shared_by": sharing_metadata["patient_address"],
            "shared_at": sharing_metadata["timestamp"],
            "expires_at": sharing_metadata["expiration"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/verify")
async def verify_purchase(request_id: str = Body(...), template_cid: str = Body(...), wallet_address: str = Body(...)):
    """
    Verify a purchase off-chain
    """
    try:
        # In a real implementation, this would:
        # 1. Retrieve the combined template package from IPFS
        # 2. Verify the hospital's signature
        # 3. For each patient template:
        #    - Retrieve the template package
        #    - Decrypt the template key
        #    - Decrypt the template data
        #    - Verify the Merkle proofs
        #    - Verify the group signature

        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is verifying purchase {request_id} with template CID {template_cid}")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to verify a purchase")

        # For demo purposes, we'll simulate this process

        # Simulate verification result
        verification_passed = True

        # Simulate list of recipients (hospital + patients)
        recipients = [
            "0x1234567890123456789012345678901234567890",  # Hospital
            "0x2345678901234567890123456789012345678901",  # Patient 1
            "0x3456789012345678901234567890123456789012"   # Patient 2
        ]

        return {
            "status": "success",
            "verified": verification_passed,
            "recipients": recipients
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/opening/compute_partial")
async def compute_partial_opening(
    opening_id: int = Body(...),
    signature: str = Body(...),
    manager_type: str = Body(...),  # "group" or "revocation"
    wallet_address: str = Body(...)
):
    """
    Compute opening off-chain (BBS04 only has one manager)
    """
    try:
        # Verify the caller is authorized using the predefined addresses

        # Check if the wallet address matches any of the role addresses
        if manager_type == "group" and wallet_address != GROUP_MANAGER_ADDRESS:
            raise HTTPException(status_code=403, detail="Not authorized as Group Manager")
        elif manager_type == "revocation" and wallet_address != REVOCATION_MANAGER_ADDRESS:
            raise HTTPException(status_code=403, detail="Not authorized as Revocation Manager")

        # Compute the opening
        open_result = open_signature_group_manager(signature)
        if open_result is None:
            # Fallback for demo purposes
            print("Warning: Signature opening failed. Using mock value.")
            open_result = {"signer": f"mock_signer_{opening_id}_{int(time.time())}"}

        return {
            "status": "success",
            "opening_id": opening_id,
            "computed": True,
            "manager_type": manager_type,
            "open_result": open_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/opening/result")
async def get_opening_result(
    opening_id: int,
    wallet_address: str,
    signature: str = None,
    partial_g: str = None,
    partial_r: str = None
):
    """
    Get the opening result (only for authorized buyer)
    """
    try:
        # Verify the caller is authorized
        # In a real implementation, we would check if the wallet address is a Buyer
        # For demo purposes, we'll allow any caller, but log the wallet address
        print(f"Opening result requested by: {wallet_address}")

        # Check if we have all the required information
        if signature and partial_g and partial_r:
            # Use the group signature utilities to open the signature
            full_open_result = open_signature_full(signature, partial_g, partial_r)

            if full_open_result is not None:
                # In a real implementation, we would use the full_open_result to get the signer's identity
                # For demo purposes, we'll use a simulated result
                signer_id = full_open_result.get("signer", f"DOCTOR_{opening_id}_ID")
            else:
                # Fallback for demo purposes
                print("Warning: Full opening failed. Using mock value.")
                signer_id = f"DOCTOR_{opening_id}_ID"
        else:
            # For demo purposes, we'll simulate this process if we don't have all the required information
            print(f"Retrieving opening result for {opening_id} (simulated)")
            signer_id = f"DOCTOR_{opening_id}_ID"

        # Simulate signer details based on the signer ID
        signer_details = {
            "name": f"Dr. Smith {opening_id}",
            "hospital": "General Hospital",
            "department": "Cardiology",
            "license": f"MD{opening_id}12345"
        }

        return {
            "status": "success",
            "opening_id": opening_id,
            "signer_id": signer_id,
            "signer_details": signer_details,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ipfs/view/{cid}")
async def view_ipfs_content(cid: str, format: str = "raw"):
    """
    View the raw content of an IPFS CID

    Args:
        cid: The IPFS CID to view
        format: The format to return the content in (raw, hex, or json)
    """
    try:
        # Clean the CID
        clean_cid_value = clean_cid(cid)
        print(f"Using cleaned CID: {clean_cid_value}")

        # Check if IPFS is connected
        if not check_ipfs_connection():
            # Try local storage
            try:
                with open(f"local_storage/{clean_cid_value}", "rb") as f:
                    content = f.read()
                print(f"Retrieved {len(content)} bytes from local storage")
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"CID not found in local storage and IPFS is not available")
        else:
            # Try to retrieve from IPFS
            try:
                content = ipfs_client.cat(clean_cid_value)
                print(f"Retrieved {len(content)} bytes from IPFS")
            except Exception as ipfs_error:
                print(f"Error retrieving from IPFS: {str(ipfs_error)}")
                # Try local storage as fallback
                try:
                    with open(f"local_storage/{clean_cid_value}", "rb") as f:
                        content = f.read()
                    print(f"Retrieved {len(content)} bytes from local storage")
                except FileNotFoundError:
                    raise HTTPException(status_code=404, detail=f"CID not found in IPFS or local storage")

        # Return the content in the requested format
        if format == "hex":
            return {"content": content.hex()}
        elif format == "json":
            try:
                # Try to parse as JSON
                if content.startswith(b"\x00"):
                    # This might be encrypted data with a nonce
                    return {
                        "type": "encrypted",
                        "nonce": content[:16].hex(),
                        "ciphertext": content[16:].hex()
                    }
                else:
                    # Try to decode as UTF-8
                    decoded = content.decode("utf-8", errors="replace")
                    try:
                        # Try to parse as JSON
                        json_data = json.loads(decoded)
                        return {"content": json_data}
                    except json.JSONDecodeError:
                        # Return as text
                        return {"content": decoded}
            except Exception as e:
                # Return as hex if JSON parsing fails
                return {"content": content.hex(), "error": str(e)}
        else:
            # Return as raw bytes (base64 encoded for the response)
            return Response(content=content, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
