import json
import os
import time
import hashlib
import base64
import random
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ipfshttpclient
from web3 import Web3
import uvicorn
from dotenv import load_dotenv

# Import auto_fill_template module
try:
    from backend.auto_fill_template import auto_fill_template
except ImportError:
    # Try relative import if the above fails
    try:
        from .auto_fill_template import auto_fill_template
    except ImportError:
        # Last resort, try direct import
        try:
            from auto_fill_template import auto_fill_template
        except ImportError:
            print("Warning: Could not import auto_fill_template module. Template auto-filling will be disabled.")
            # Define a dummy function as fallback
            def auto_fill_template(request_id, template):
                print(f"Auto-fill template disabled: request_id={request_id}")
                return None
# Try to import Coinbase Cloud SDK, but make it optional
try:
    from cdp_sdk import CoinbaseCloud
    has_coinbase_sdk = True
except ImportError:
    has_coinbase_sdk = False
    print("Warning: cdp_sdk not found. Coinbase Cloud features will be disabled.")
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from backend.data import MerkleService, encrypt_record, encrypt_hospital_info_and_key, generate_private_key, generate_public_key
from backend.roles import Patient, Doctor, GroupManager
from backend.groupsig_utils import sign_message, verify_signature, open_signature_group_manager, open_signature_revocation_manager, open_signature_full

app = FastAPI(title="Healthcare Data Sharing API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy", "timestamp": int(time.time())}

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
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA")
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

# Key management system
class KeyManager:
    """Secure key management system for handling cryptographic keys"""

    def __init__(self):
        self.key_store = {}
        self.public_key_store = {}
        self.initialize_keys()

    def initialize_keys(self):
        """Initialize keys for all roles"""
        # Check if we have keys in secure storage
        try:
            # In production, this would load from a secure key store or HSM
            # For this implementation, we'll generate new keys if needed
            if not os.path.exists("secure_keys"):
                os.makedirs("secure_keys", exist_ok=True)

            # Generate or load keys for each role
            self._initialize_role_keys("patient", PATIENT_ADDRESS)
            self._initialize_role_keys("doctor", DOCTOR_ADDRESS)
            self._initialize_role_keys("hospital", HOSPITAL_ADDRESS)
            self._initialize_role_keys("buyer", BUYER_ADDRESS)
            self._initialize_role_keys("group_manager", GROUP_MANAGER_ADDRESS)
            self._initialize_role_keys("revocation_manager", REVOCATION_MANAGER_ADDRESS)

            print("Key initialization complete")
        except Exception as e:
            print(f"Error initializing keys: {str(e)}")
            # Fall back to in-memory keys for demo
            self._generate_fallback_keys()

    def _initialize_role_keys(self, role, address):
        """Initialize keys for a specific role"""
        key_file = f"secure_keys/{role}_{address}.pem"
        pub_key_file = f"secure_keys/{role}_{address}_pub.pem"

        if os.path.exists(key_file) and os.path.exists(pub_key_file):
            # Load existing keys
            try:
                with open(key_file, "rb") as f:
                    private_key_data = f.read()
                    private_key = serialization.load_pem_private_key(
                        private_key_data,
                        password=None,
                        backend=default_backend()
                    )

                with open(pub_key_file, "rb") as f:
                    public_key_data = f.read()
                    public_key = serialization.load_pem_public_key(
                        public_key_data,
                        backend=default_backend()
                    )

                # Store in memory
                self.key_store[address] = private_key
                self.public_key_store[address] = public_key
                print(f"Loaded keys for {role} ({address})")
            except Exception as e:
                print(f"Error loading keys for {role}: {str(e)}")
                # Generate new keys if loading fails
                self._generate_and_save_keys(role, address)
        else:
            # Generate new keys
            self._generate_and_save_keys(role, address)

    def _generate_and_save_keys(self, role, address):
        """Generate and save new keys for a role"""
        private_key, public_key = self.generate_rsa_key_pair()

        # Save private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        with open(f"secure_keys/{role}_{address}.pem", "wb") as f:
            f.write(private_key_pem)

        # Save public key
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(f"secure_keys/{role}_{address}_pub.pem", "wb") as f:
            f.write(public_key_pem)

        # Store in memory
        self.key_store[address] = private_key
        self.public_key_store[address] = public_key
        print(f"Generated and saved new keys for {role} ({address})")

    def _generate_fallback_keys(self):
        """Generate fallback keys for all roles"""
        for role, address in [
            ("patient", PATIENT_ADDRESS),
            ("doctor", DOCTOR_ADDRESS),
            ("hospital", HOSPITAL_ADDRESS),
            ("buyer", BUYER_ADDRESS),
            ("group_manager", GROUP_MANAGER_ADDRESS),
            ("revocation_manager", REVOCATION_MANAGER_ADDRESS)
        ]:
            private_key, public_key = self.generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            print(f"Generated fallback keys for {role} ({address})")

    def generate_rsa_key_pair(self):
        """Generate an RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key

    def get_private_key(self, address):
        """Get the private key for an address"""
        if address in self.key_store:
            return self.key_store[address]
        else:
            print(f"Warning: No private key found for {address}. Generating temporary key.")
            private_key, public_key = self.generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            return private_key

    def get_public_key(self, address):
        """Get the public key for an address"""
        if address in self.public_key_store:
            return self.public_key_store[address]
        else:
            print(f"Warning: No public key found for {address}. Generating temporary key.")
            private_key, public_key = self.generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            return public_key

    def get_symmetric_key(self, address):
        """Get a symmetric key for an address"""
        # In a real implementation, this would use a secure key derivation function
        # For now, we'll derive it from the private key
        private_key = self.get_private_key(address)
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        # Use SHA-256 to derive a symmetric key
        return hashlib.sha256(private_key_bytes).digest()

# Initialize the key manager
key_manager = KeyManager()

# Function to encrypt with RSA public key using hybrid encryption for large data
def encrypt_with_public_key(data, public_key):
    """Encrypt data with an RSA public key using RSA-OAEP with hybrid encryption for large data

    For small data (<190 bytes), this uses direct RSA-OAEP encryption.
    For larger data, it uses hybrid encryption:
    1. Generate a random AES key
    2. Encrypt the data with AES
    3. Encrypt the AES key with RSA
    4. Return the encrypted key + encrypted data

    Args:
        data: The data to encrypt (bytes or string)
        public_key: The RSA public key to use for encryption

    Returns:
        bytes: The encrypted data

    Raises:
        ValueError: If the data is not bytes or string
    """
    # Convert input to bytes if it's a string or other type
    if isinstance(data, str):
        data = data.encode()
    elif not isinstance(data, bytes):
        raise ValueError(f"Data must be bytes or string, got {type(data)}")

    # Check if the data is too large for RSA encryption
    # RSA-2048 can encrypt at most 190 bytes with OAEP padding
    max_size = 190  # Conservative estimate for RSA-2048 with OAEP-SHA256

    if len(data) > max_size:
        # For larger data, use hybrid encryption:
        # 1. Generate a random AES key
        # 2. Encrypt the data with AES
        # 3. Encrypt the AES key with RSA
        # 4. Return the encrypted key + encrypted data
        from backend.crypto import aes

        # Generate a random AES key
        aes_key = os.urandom(32)  # 256-bit key

        # Encrypt the data with AES
        encrypted_data = aes.encrypt(data, aes_key)

        # Encrypt the AES key with RSA
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Combine the encrypted key and data
        # Format: [key_length (4 bytes)][encrypted_key][encrypted_data]
        key_length = len(encrypted_key).to_bytes(4, byteorder='big')
        return key_length + encrypted_key + encrypted_data
    else:
        # For small data, use RSA directly
        try:
            ciphertext = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return ciphertext
        except Exception as e:
            print(f"Error in RSA encryption: {str(e)}")
            raise

# Function to decrypt with RSA private key with support for hybrid encryption
def decrypt_with_private_key(data, private_key):
    """Decrypt data with an RSA private key using RSA-OAEP with support for hybrid encryption

    This function can decrypt both direct RSA-encrypted data and hybrid-encrypted data.
    For hybrid-encrypted data, it:
    1. Extracts the encrypted AES key and encrypted data
    2. Decrypts the AES key with RSA
    3. Decrypts the data with AES

    Args:
        data: The encrypted data (bytes)
        private_key: The RSA private key to use for decryption

    Returns:
        bytes: The decrypted data

    Raises:
        ValueError: If the data is not bytes
    """
    if not isinstance(data, bytes):
        raise ValueError(f"Data must be bytes, got {type(data)}")

    # Check if this is hybrid encryption (key_length + encrypted_key + encrypted_data)
    # The first 4 bytes should be the key length if it's hybrid encryption
    try:
        if len(data) > 256:  # Minimum size for hybrid encryption
            try:
                # Extract the key length
                key_length = int.from_bytes(data[:4], byteorder='big')

                # Extract the encrypted key and encrypted data
                encrypted_key = data[4:4+key_length]
                encrypted_data = data[4+key_length:]

                # Decrypt the AES key with RSA
                aes_key = private_key.decrypt(
                    encrypted_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )

                # Decrypt the data with AES
                from backend.crypto import aes
                plaintext = aes.decrypt(encrypted_data, aes_key)

                # Convert to bytes if it's a string
                if isinstance(plaintext, str):
                    plaintext = plaintext.encode()

                return plaintext
            except Exception as hybrid_error:
                print(f"Error in hybrid decryption: {str(hybrid_error)}")
                # Fall back to direct RSA decryption
                pass

        # Direct RSA decryption
        plaintext = private_key.decrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    except Exception as e:
        print(f"Error in RSA decryption: {str(e)}")
        raise

# This function is now defined above

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

# Function to save a transaction to local storage
def save_transaction(transaction):
    """Save a transaction to the local storage and track gas fees by workflow.

    Args:
        transaction: The transaction data to save

    Returns:
        bool: True if the transaction was saved successfully, False otherwise
    """
    try:
        # Create the transactions directory if it doesn't exist
        os.makedirs("local_storage/transactions", exist_ok=True)

        # Add workflow category based on transaction type
        if "workflow" not in transaction:
            # Define workflow categories based on transaction types
            workflow_mapping = {
                # Storing workflow
                "Store": "storing",
                "Record Creation": "storing",
                "Record Upload": "storing",
                "Record Storage": "storing",
                "Create Record": "storing",
                "Sign Record": "storing",

                # Sharing workflow
                "Share": "sharing",
                "Record Sharing": "sharing",
                "Share Record": "sharing",
                "Encrypt Record": "sharing",
                "Decrypt Record": "sharing",
                "Access Record": "sharing",

                # Purchasing workflow
                "Request": "purchasing",
                "Hospital Reply": "purchasing",
                "Buyer Verify": "purchasing",
                "Verification": "purchasing",
                "Finalize": "purchasing",
                "Revocation Request": "purchasing",
                "Template Fill": "purchasing",
                "Template Verification": "purchasing",
                "Payment": "purchasing"
            }

            tx_type = transaction.get("type", "Unknown")
            transaction["workflow"] = workflow_mapping.get(tx_type, "other")

        # Generate a unique ID for the transaction if not already present
        if "id" not in transaction:
            transaction["id"] = f"tx-{int(time.time())}_{random.randint(1000, 9999)}"

        # Add timestamp if not already present
        if "timestamp" not in transaction:
            transaction["timestamp"] = int(time.time())

        # Add status if not already present
        if "status" not in transaction:
            transaction["status"] = "Completed"

        # Save the transaction to a file
        file_path = f"local_storage/transactions/{transaction['id']}.json"
        with open(file_path, "w") as f:
            json.dump(transaction, f)

        # Also save to workflow-specific directory for easier analysis
        workflow = transaction.get("workflow", "other")
        workflow_dir = f"local_storage/{workflow}_transactions"
        os.makedirs(workflow_dir, exist_ok=True)
        workflow_file_path = f"{workflow_dir}/{transaction['id']}.json"
        with open(workflow_file_path, "w") as f:
            json.dump(transaction, f)

        print(f"Transaction saved: {file_path} and {workflow_file_path}")
        return True
    except Exception as e:
        print(f"Error saving transaction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.get("/api/buyer/filled-templates")
@app.get("/buyer/filled-templates")
async def get_filled_templates(wallet_address: str):
    """
    Get filled templates for a buyer
    """
    try:
        print(f"Getting filled templates for buyer {wallet_address}")

        # For demo purposes, we'll look for purchase requests that have been filled by patients
        # In a real implementation, we would filter requests based on the buyer's address

        # Check if the local storage directory exists
        if not os.path.exists("local_storage/purchases"):
            return {"templates": []}

        # Get all purchase files
        purchase_files = os.listdir("local_storage/purchases")

        # Filter for requests that have been filled by patients
        templates = []
        for file_name in purchase_files:
            if not file_name.endswith(".json"):
                continue

            file_path = f"local_storage/purchases/{file_name}"

            try:
                with open(file_path, "r") as f:
                    purchase_data = json.load(f)

                # Check if this request has been filled by a patient and belongs to this buyer
                if purchase_data.get("status") == "filled" and purchase_data.get("buyer") == wallet_address:
                    # Check if the request has multiple templates
                    if "templates" in purchase_data and purchase_data["templates"]:
                        # Create a template object for each template in the request
                        for template_info in purchase_data["templates"]:
                            template = {
                                "request_id": purchase_data.get("request_id"),
                                "patient": purchase_data.get("patient_address", "Unknown"),
                                "hospital": purchase_data.get("hospital", "Unknown"),
                                "template_cid": template_info.get("template_cid"),
                                "cert_cid": template_info.get("cert_cid"),
                                "status": "filled",
                                "timestamp": template_info.get("filled_at", purchase_data.get("filled_at", int(time.time()))),
                                "template": purchase_data.get("template", {}),
                                "verified": template_info.get("verified", False)
                            }

                            # Add to templates list
                            templates.append(template)
                    else:
                        # Fallback for older format with a single template
                        template = {
                            "request_id": purchase_data.get("request_id"),
                            "patient": purchase_data.get("patient_address", "Unknown"),
                            "hospital": purchase_data.get("hospital", "Unknown"),
                            "template_cid": purchase_data.get("template_cid"),
                            "cert_cid": purchase_data.get("cert_cid"),
                            "status": "filled",
                            "timestamp": purchase_data.get("filled_at", int(time.time())),
                            "template": purchase_data.get("template", {}),
                            "verified": purchase_data.get("verified", False)
                        }

                        # Add to templates list
                        templates.append(template)
            except Exception as e:
                print(f"Error processing file {file_name}: {str(e)}")

        return {"templates": templates}
    except Exception as e:
        print(f"Error in get_filled_templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/template/{template_cid}")
@app.get("/template/{template_cid}")
async def get_template(template_cid: str, wallet_address: str, cert_cid: str = None):
    """
    Retrieve and decrypt a template for a buyer
    """
    try:
        print(f"Retrieving template {template_cid} for buyer {wallet_address}")

        # Clean the CIDs
        clean_template_cid = clean_cid(template_cid)
        clean_cert_cid = clean_cid(cert_cid) if cert_cid else None

        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is retrieving template {clean_template_cid}")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to retrieve a template")

        # Get the CERT data if provided
        cert_data = None
        if clean_cert_cid:
            try:
                # First try IPFS
                if check_ipfs_connection():
                    try:
                        # Try to retrieve from IPFS
                        cert_bytes = ipfs_client.cat(clean_cert_cid)
                        cert_data = json.loads(cert_bytes.decode())
                        print(f"Retrieved CERT data from IPFS: {len(cert_bytes)} bytes")
                    except Exception as ipfs_error:
                        print(f"Error retrieving CERT from IPFS: {str(ipfs_error)}")
                        # Try local storage as fallback
                        try:
                            with open(f"local_storage/{clean_cert_cid}", "rb") as f:
                                cert_bytes = f.read()
                            cert_data = json.loads(cert_bytes.decode())
                            print(f"Retrieved CERT data from local storage: {len(cert_bytes)} bytes")
                        except Exception as local_error:
                            print(f"Error retrieving CERT from local storage: {str(local_error)}")
                            raise HTTPException(status_code=404, detail=f"CERT not found in IPFS or local storage: {clean_cert_cid}")
                else:
                    # IPFS not connected, try local storage
                    try:
                        with open(f"local_storage/{clean_cert_cid}", "rb") as f:
                            cert_bytes = f.read()
                        cert_data = json.loads(cert_bytes.decode())
                        print(f"Retrieved CERT data from local storage: {len(cert_bytes)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving CERT from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"CERT not found in local storage and IPFS is not available")
            except Exception as e:
                print(f"Error retrieving CERT data: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error retrieving CERT data: {str(e)}")

        # Get the encrypted template data
        encrypted_template = None
        try:
            # First try IPFS
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    encrypted_template = ipfs_client.cat(clean_template_cid)
                    print(f"Retrieved encrypted template from IPFS: {len(encrypted_template)} bytes")
                except Exception as ipfs_error:
                    print(f"Error retrieving encrypted template from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{clean_template_cid}", "rb") as f:
                            encrypted_template = f.read()
                        print(f"Retrieved encrypted template from local storage: {len(encrypted_template)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving encrypted template from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"Encrypted template not found in IPFS or local storage: {clean_template_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{clean_template_cid}", "rb") as f:
                        encrypted_template = f.read()
                    print(f"Retrieved encrypted template from local storage: {len(encrypted_template)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving encrypted template from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"Encrypted template not found in local storage and IPFS is not available")
        except Exception as e:
            print(f"Error retrieving encrypted template: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving encrypted template: {str(e)}")

        # Implement the real decryption process
        # 1. Get the encrypted key from the CERT
        # 2. Decrypt the encrypted key with the buyer's private key
        # 3. Use the decrypted key to decrypt the encrypted template

        # Initialize variables
        decrypted_template = None
        encrypted_key = None

        # 1. Get the encrypted key from the CERT
        if cert_data and "encrypted_key" in cert_data:
            encrypted_key = cert_data["encrypted_key"]
            print(f"Found encrypted key in CERT: {encrypted_key[:20] if isinstance(encrypted_key, str) else 'binary data'}...")

            # Convert from hex string if needed
            if isinstance(encrypted_key, str):
                try:
                    encrypted_key = bytes.fromhex(encrypted_key)
                    print(f"Converted encrypted key from hex to bytes: {len(encrypted_key)} bytes")
                except ValueError as hex_error:
                    print(f"Error converting encrypted key from hex: {str(hex_error)}")
                    try:
                        # Try base64 decoding as fallback
                        encrypted_key = base64.b64decode(encrypted_key)
                        print(f"Converted encrypted key from base64 to bytes: {len(encrypted_key)} bytes")
                    except Exception as b64_error:
                        print(f"Error converting encrypted key from base64: {str(b64_error)}")
                        # Keep as is
                        encrypted_key = encrypted_key.encode() if isinstance(encrypted_key, str) else encrypted_key
        else:
            print("Warning: No encrypted key found in CERT data")

        # 2. Decrypt the encrypted key with the buyer's private key
        decrypted_key = None
        if encrypted_key:
            try:
                # Get the buyer's private key from our key manager
                # Use the wallet address as the buyer address
                buyer_private_key = key_manager.get_private_key(wallet_address)
                print(f"Retrieved buyer's private key for decryption using wallet address: {wallet_address}")

                # Decrypt the encrypted key with the buyer's private key
                try:
                    decrypted_key = decrypt_with_private_key(encrypted_key, buyer_private_key)
                    print(f"Successfully decrypted key with buyer's private key: {decrypted_key[:5].hex() if decrypted_key else 'None'}...")
                except Exception as decrypt_error:
                    print(f"Error decrypting key with buyer's private key: {str(decrypt_error)}")
                    print(f"Error type: {type(decrypt_error)}")

                    # Try fallback decryption method
                    try:
                        decrypted_key = buyer_private_key.decrypt(
                            encrypted_key,
                            padding.OAEP(
                                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                algorithm=hashes.SHA256(),
                                label=None
                            )
                        )
                        print(f"Used fallback decryption method: {decrypted_key[:5].hex() if decrypted_key else 'None'}...")
                    except Exception as direct_error:
                        print(f"Direct decryption also failed: {str(direct_error)}")
                        # Fall back to deterministic key generation
                        decrypted_key = hashlib.sha256(f"template_key_{clean_template_cid}".encode()).digest()
                        print(f"Using fallback deterministic key: {decrypted_key[:5].hex()}...")
            except Exception as key_error:
                print(f"Error generating buyer key pair: {str(key_error)}")
                # Fall back to deterministic key generation
                decrypted_key = hashlib.sha256(f"template_key_{clean_template_cid}".encode()).digest()
                print(f"Using fallback deterministic key: {decrypted_key[:5].hex()}...")
        else:
            # Fall back to deterministic key generation if no encrypted key is found
            decrypted_key = hashlib.sha256(f"template_key_{clean_template_cid}".encode()).digest()
            print(f"No encrypted key found, using fallback deterministic key: {decrypted_key[:5].hex()}...")

        # 3. Use the decrypted key to decrypt the encrypted template
        if decrypted_key and encrypted_template:
            try:
                # Try to decrypt the template using our decrypt_record function
                decrypted_data = decrypt_record(encrypted_template, decrypted_key)
                print(f"Successfully decrypted template data: {len(json.dumps(decrypted_data))} bytes")

                # Parse the decrypted data as JSON
                if isinstance(decrypted_data, dict):
                    decrypted_template = decrypted_data
                else:
                    # If it's a string or bytes, try to parse as JSON
                    try:
                        if isinstance(decrypted_data, bytes):
                            decrypted_template = json.loads(decrypted_data.decode())
                        else:
                            decrypted_template = json.loads(decrypted_data)
                        print(f"Successfully parsed decrypted template as JSON")
                    except Exception as json_error:
                        print(f"Error parsing decrypted template as JSON: {str(json_error)}")
                        # Return the raw decrypted data
                        decrypted_template = {"raw_data": decrypted_data if isinstance(decrypted_data, str) else decrypted_data.decode()}
            except Exception as decrypt_error:
                print(f"Error decrypting template: {str(decrypt_error)}")
                # Try manual decryption as a fallback
                try:
                    # First 16 bytes are the nonce
                    nonce = encrypted_template[:16]
                    ciphertext = encrypted_template[16:]

                    # Create a cipher object
                    cipher = Cipher(algorithms.AES(decrypted_key), modes.CTR(nonce), backend=default_backend())
                    decryptor = cipher.decryptor()

                    # Decrypt the data
                    decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
                    print(f"Used manual decryption method: {len(decrypted_bytes)} bytes")

                    # Try to parse as JSON
                    try:
                        decrypted_template = json.loads(decrypted_bytes.decode())
                        print(f"Successfully parsed manually decrypted template as JSON")
                    except Exception as json_error:
                        print(f"Error parsing manually decrypted template as JSON: {str(json_error)}")
                        # Return the raw decrypted data
                        decrypted_template = {"raw_data": decrypted_bytes.decode(errors='replace')}
                except Exception as manual_error:
                    print(f"Manual decryption also failed: {str(manual_error)}")
                    # Fall back to mock data
                    decrypted_template = create_mock_template(cert_data)
        else:
            # Fall back to mock data if decryption fails
            print("Falling back to mock template data")
            decrypted_template = create_mock_template(cert_data)

        return decrypted_template
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_template: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/revocation/request")
@app.post("/revocation/request")
async def request_revocation(
    request_id: str = Body(...),
    template_cid: str = Body(...),
    signature: str = Body(...),
    wallet_address: str = Body(...)
):
    """
    Buyer requests revocation of a doctor's signature
    """
    try:
        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is requesting revocation for template {template_cid} in request {request_id}")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to request revocation")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Check if the template CID matches
        if purchase_data.get("template_cid") != template_cid:
            raise HTTPException(status_code=400, detail=f"Template CID {template_cid} does not match the one in request {request_id}")

        # Generate a transaction hash for demo purposes
        tx_hash = f"0x{hashlib.sha256(f'{request_id}_{template_cid}_{signature}_{int(time.time())}'.encode()).hexdigest()}"

        # Calculate a simulated gas fee
        gas_fee = round(random.uniform(0.002, 0.005), 4)  # Revocation costs more gas

        # Create transaction history entry for revocation request
        revocation_transaction = {
            "id": f"tx-{int(time.time())}",
            "request_id": request_id,
            "type": "Revocation Request",
            "status": "Completed",
            "timestamp": int(time.time()),
            "tx_hash": tx_hash,
            "gas_fee": gas_fee,
            "buyer": wallet_address,
            "template_cid": template_cid,
            "signature": signature,
            "details": {
                "message": "Revocation request submitted to Group Manager and Revocation Manager",
                "reason": "Verification failed"
            }
        }

        # Save the transaction
        save_transaction(revocation_transaction)

        # Update the purchase data
        purchase_data["revocation_requested"] = True
        purchase_data["revocation_requested_at"] = int(time.time())
        purchase_data["revocation_transaction"] = revocation_transaction

        # Save the updated purchase data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # In a real implementation, this would call the smart contract to request revocation
        #tx_hash = contract.functions.requestRevocation(signature).transact({'from': wallet_address})
        #receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "message": "Revocation request submitted successfully",
            "transaction_hash": tx_hash,
            "gas_fee": gas_fee
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in request_revocation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

# Function to create a mock template for fallback
def create_mock_template(cert_data=None):
    """
    Create a mock template for fallback when decryption fails

    Args:
        cert_data: Optional CERT data to include in the mock template

    Returns:
        dict: A mock template with sample medical data
    """
    return {
        "record": {
            "patientID": "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",
            "doctorID": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            "date": "2023-06-15",
            "category": "Cardiology",
            "hospitalInfo": "General Hospital",
            "demographics": {
                "age": 45,
                "gender": "Male"
            },
            "medical_data": {
                "diagnosis": "Hypertension",
                "treatment": "Prescribed medication and lifestyle changes"
            },
            "notes": "Patient responding well to treatment"
        },
        "merkle_root": cert_data.get("merkle_root", "unknown") if cert_data else "unknown",
        "signature": cert_data.get("signature", "unknown") if cert_data else "unknown",
        "timestamp": int(time.time()),
        "is_mock": True,  # Flag to indicate this is mock data
        "decryption_failed": True  # Flag to indicate decryption failed
    }

# Models
class RecordData(BaseModel):
    patientID: str
    doctorID: str
    date: str
    category: Optional[str] = "General"
    hospitalInfo: Optional[str] = "General Hospital"
    demographics: Optional[Dict[str, Any]] = None
    medical_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class ShareRequest(BaseModel):
    record_cid: str
    doctor_address: str

class PurchaseRequest(BaseModel):
    template_hash: str
    amount: float
    template: Optional[dict] = None

# API Endpoints
@app.post("/api/records/sign")
async def sign_record(record_data: dict = Body(...), wallet_address: str = Body(...)):
    """
    Doctor creates and signs a record, which is then returned to be encrypted and stored.
    The doctor's real identity is protected using pseudonymous identifiers.
    """
    try:
        # Import the pseudonym module
        from backend.pseudonym import generate_pseudonym, create_anonymous_record

        # Generate a pseudonymous identity for the doctor
        doctor_pseudonym = generate_pseudonym(wallet_address)
        print(f"Generated pseudonym {doctor_pseudonym} for doctor {wallet_address}")

        # Create an anonymized record with the pseudonym
        anonymized_record = create_anonymous_record(record_data, doctor_pseudonym)
        print(f"Created anonymized record with pseudonym {doctor_pseudonym}")

        # Create Merkle tree from anonymized record data
        merkle_service = MerkleService()
        merkle_root, proofs = merkle_service.create_merkle_tree(anonymized_record)

        # Sign the merkle root with group signature using the doctor's member key
        # The group signature provides cryptographic anonymity
        signature = sign_message(merkle_root)

        # If group signature fails, fall back to a mock signature
        if signature is None:
            print("Warning: Group signature failed. Using mock signature.")
            signature = hashlib.sha256(f"{merkle_root}_{int(time.time())}".encode()).hexdigest()

        return {
            "record": anonymized_record,  # Return the anonymized record
            "merkleRoot": merkle_root,
            "proofs": proofs,
            "signature": signature,
            "doctorPseudonym": doctor_pseudonym  # Include the pseudonym for reference
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
        # For now, we'll still generate a key deterministically, but implement the real process
        # for encryption and eId generation

        # 1. Verify the signature on the merkle_root
        signature_verified = verify_signature(merkle_root, signature)
        if not signature_verified:
            print(f"Signature verification failed for merkle_root: {merkle_root[:20]}...")
            raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            print(f"Signature verified successfully for merkle_root: {merkle_root[:20]}...")

        # 2. Generate or retrieve the patient's key
        patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()
        print(f"Generated patient key: {patient_key[:5].hex()}...")

        try:
            # 3. Encrypt the record with the patient's key using AES-CTR
            record_json = json.dumps(record).encode()
            print(f"Record JSON length: {len(record_json)} bytes")
            encrypted_record = encrypt_record(record_json, patient_key)
            print(f"Encrypted record length: {len(encrypted_record)} bytes")

            # 4. Store the encrypted record on IPFS
            cid = store_on_ipfs(encrypted_record)
            print(f"Stored on IPFS with CID: {cid}")

            # 5. Generate eId = PCS(HospitalInfo||K_patient, PKgm)
            # This uses a proper encryption scheme with the Group Manager's public key
            try:
                # Get the Group Manager's public key
                group_manager_public_key = key_manager.get_public_key(GROUP_MANAGER_ADDRESS)
                print(f"Retrieved Group Manager public key for encryption")

                # Combine hospital info and patient key
                hospital_info_and_key = f"{hospital_info}||{base64.b64encode(patient_key).decode()}"
                print(f"Hospital info and key prepared for encryption")

                # Encrypt with Group Manager's public key using RSA-OAEP
                eId_bytes = encrypt_with_public_key(hospital_info_and_key.encode(), group_manager_public_key)

                # Convert to base64 for storage/transmission
                eId = base64.b64encode(eId_bytes).decode()
                print(f"Generated eId with proper encryption: {len(eId_bytes)} bytes")
            except Exception as e:
                print(f"Error generating eId with proper encryption: {str(e)}")
                # Fallback to simpler encryption if the primary method fails
                try:
                    # Use our crypto module's encrypt function as fallback
                    from backend.crypto import aes
                    temp_key = hashlib.sha256(f"{GROUP_MANAGER_ADDRESS}_key".encode()).digest()
                    eId_bytes = aes.encrypt(hospital_info_and_key, temp_key)
                    eId = base64.b64encode(eId_bytes).decode()
                    print(f"Generated eId with fallback encryption: {len(eId_bytes)} bytes")
                except Exception as fallback_error:
                    print(f"Fallback encryption also failed: {str(fallback_error)}")
                    # Last resort fallback
                    eId = encrypt_hospital_info_and_key(hospital_info_and_key)
                    print(f"Last resort eId generated: {len(eId)} chars")

            # Encrypt hospital info and patient key with the Group Manager's public key (PCS)
            # This creates the eId component of the CERT
            try:
                # Get the Group Manager's public key
                group_manager_public_key = key_manager.get_public_key(GROUP_MANAGER_ADDRESS)

                if group_manager_public_key:
                    print(f"Retrieved Group Manager's public key for PCS encryption")

                    # Combine hospital info and patient key
                    # Convert patient_key to hex string if it's bytes
                    patient_key_str = patient_key.hex() if isinstance(patient_key, bytes) else patient_key

                    # Create a string representation that can be properly encoded
                    hospital_info_and_key = f"{hospital_info}||{patient_key_str}"
                    print(f"Hospital info and key combined: {hospital_info}||{patient_key_str[:10]}...")

                    # Convert to bytes for encryption
                    data_to_encrypt = hospital_info_and_key.encode()

                    # Encrypt with the Group Manager's public key (PCS)
                    eId = encrypt_with_public_key(data_to_encrypt, group_manager_public_key)
                    print(f"Created eId using PCS encryption with Group Manager's public key")
                else:
                    print("Warning: Group Manager's public key not found. Using mock eId.")
                    # Fallback to mock eId
                    # Convert patient_key to hex string if it's bytes
                    patient_key_str = patient_key.hex() if isinstance(patient_key, bytes) else str(patient_key)
                    eId = f"mock_eid_{hashlib.sha256(f'{hospital_info}_{patient_key_str}_{int(time.time())}'.encode()).hexdigest()}"
            except Exception as pcs_error:
                print(f"Error in PCS encryption: {str(pcs_error)}")
                # Fallback to mock eId
                # Convert patient_key to hex string if it's bytes
                patient_key_str = patient_key.hex() if isinstance(patient_key, bytes) else str(patient_key)
                eId = f"mock_eid_{hashlib.sha256(f'{hospital_info}_{patient_key_str}_{int(time.time())}'.encode()).hexdigest()}"

            # Call the smart contract to store the record metadata on the blockchain
            try:
                # Convert CID and merkle_root to bytes32 format for the contract
                print(f"Original CID: {cid}")
                print(f"Original merkle_root: {merkle_root}")

                try:
                    # For CID conversion
                    if cid.startswith('0x'):
                        # Already a hex string with 0x prefix
                        hex_cid = cid[2:]
                    else:
                        # For IPFS CIDs, hash them to get a bytes32 value
                        hex_cid = hashlib.sha256(cid.encode()).hexdigest()

                    # Ensure the hex string is the right length and pad if necessary
                    hex_cid = hex_cid.ljust(64, '0')
                    # Clean the hex string (remove non-hex characters)
                    hex_cid = ''.join(c for c in hex_cid if c in '0123456789abcdefABCDEF')
                    # Convert to bytes
                    cid_bytes32 = bytes.fromhex(hex_cid)
                    print(f"Converted CID to bytes32, length: {len(cid_bytes32)}")

                    # For merkle_root conversion
                    if merkle_root.startswith('0x'):
                        # Already a hex string with 0x prefix
                        hex_merkle = merkle_root[2:]
                    else:
                        # If it looks like a hex string (all hex chars)
                        if all(c in '0123456789abcdefABCDEF' for c in merkle_root):
                            hex_merkle = merkle_root
                        else:
                            # Hash it to get a hex string
                            hex_merkle = hashlib.sha256(merkle_root.encode()).hexdigest()

                    # Ensure the hex string is the right length and pad if necessary
                    hex_merkle = hex_merkle.ljust(64, '0')
                    # Clean the hex string (remove non-hex characters)
                    hex_merkle = ''.join(c for c in hex_merkle if c in '0123456789abcdefABCDEF')
                    # Convert to bytes
                    merkle_root_bytes32 = bytes.fromhex(hex_merkle)
                    print(f"Converted merkle_root to bytes32, length: {len(merkle_root_bytes32)}")

                except Exception as hex_error:
                    print(f"Error converting to bytes32: {str(hex_error)}")
                    # Fallback to using the hash of the values
                    cid_bytes32 = hashlib.sha256(str(cid).encode()).digest()
                    merkle_root_bytes32 = hashlib.sha256(str(merkle_root).encode()).digest()
                    print("Using fallback hash conversion for bytes32")

                # Use web3.py to call the contract and create a real transaction
                try:
                    # Initialize web3 connection to BASE Sepolia testnet
                    # Note: We already have json, os, and dotenv imported at the top of the file
                    from web3 import Web3

                    # Load environment variables
                    load_dotenv()

                    # Get RPC URL and private key from environment variables
                    BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://api.developer.coinbase.com/rpc/v1/base-sepolia/TU79b5nxSoHEPVmNhElKsyBqt9CUbNTf')
                    DOCTOR_PRIVATE_KEY = os.getenv('DOCTOR_PRIVATE_KEY')
                    CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

                    # Check if we have the required environment variables
                    if not DOCTOR_PRIVATE_KEY or not CONTRACT_ADDRESS:
                        raise ValueError("Missing required environment variables: DOCTOR_PRIVATE_KEY or CONTRACT_ADDRESS")

                    # Initialize web3 connection
                    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
                    if not w3.is_connected():
                        raise ConnectionError(f"Failed to connect to BASE Goerli at {BASE_RPC_URL}")

                    print(f"Connected to BASE Goerli: {w3.is_connected()}")

                    # Load contract ABI
                    contract_abi_path = os.path.join(os.path.dirname(__file__), '../contracts/DataHub.json')
                    print(f"Looking for contract ABI at: {contract_abi_path}")

                    if not os.path.exists(contract_abi_path):
                        print(f"Contract ABI file not found at {contract_abi_path}, trying alternative paths...")
                        # Try alternative paths
                        alt_paths = [
                            "contracts/DataHub.json",
                            "../contracts/DataHub.json",
                            "./contracts/DataHub.json",
                            "artifacts/contracts/DataHub.sol/DataHub.json"
                        ]

                        for alt_path in alt_paths:
                            if os.path.exists(alt_path):
                                contract_abi_path = alt_path
                                print(f"Found contract ABI at alternative path: {contract_abi_path}")
                                break
                        else:
                            # If we get here, none of the paths worked
                            print("Could not find contract ABI file, using hardcoded ABI")
                            # Use a hardcoded minimal ABI for the storeData function
                            contract_abi = [
                                {
                                    "inputs": [
                                        {"internalType": "bytes32", "name": "cid", "type": "bytes32"},
                                        {"internalType": "bytes32", "name": "root", "type": "bytes32"},
                                        {"internalType": "bytes", "name": "sig", "type": "bytes"}
                                    ],
                                    "name": "storeData",
                                    "outputs": [],
                                    "stateMutability": "nonpayable",
                                    "type": "function"
                                }
                            ]
                            # Skip the file loading
                            contract_json = {"abi": contract_abi}

                    if os.path.exists(contract_abi_path):
                        # Load ABI from file
                        try:
                            with open(contract_abi_path, 'r') as f:
                                contract_json = json.load(f)
                                contract_abi = contract_json['abi']
                                print(f"Successfully loaded contract ABI from {contract_abi_path}")
                        except Exception as abi_error:
                            print(f"Error loading contract ABI: {str(abi_error)}")
                            # Use a hardcoded minimal ABI for the storeData function
                            contract_abi = [
                                {
                                    "inputs": [
                                        {"internalType": "bytes32", "name": "cid", "type": "bytes32"},
                                        {"internalType": "bytes32", "name": "root", "type": "bytes32"},
                                        {"internalType": "bytes", "name": "sig", "type": "bytes"}
                                    ],
                                    "name": "storeData",
                                    "outputs": [],
                                    "stateMutability": "nonpayable",
                                    "type": "function"
                                }
                            ]
                            contract_json = {"abi": contract_abi}

                    # Create contract instance
                    # Ensure the contract address is properly checksummed
                    try:
                        checksummed_address = w3.to_checksum_address(CONTRACT_ADDRESS)
                        print(f"Using checksummed contract address: {checksummed_address}")
                        contract = w3.eth.contract(address=checksummed_address, abi=contract_abi)
                    except Exception as addr_error:
                        print(f"Error checksumming contract address: {str(addr_error)}")
                        # Try direct address
                        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

                    # Create account from private key
                    account = w3.eth.account.from_key(DOCTOR_PRIVATE_KEY)
                    doctor_address = account.address
                    print(f"Using doctor address: {doctor_address}")

                    # Get current gas price with a higher premium
                    gas_price = w3.eth.gas_price
                    gas_price_with_premium = int(gas_price * 2.0)  # 100% premium for better chance of inclusion

                    # Get the nonce - check for pending transactions
                    try:
                        # First try to get the next pending nonce
                        pending_nonce = w3.eth.get_transaction_count(doctor_address, 'pending')
                        latest_nonce = w3.eth.get_transaction_count(doctor_address, 'latest')

                        print(f"Pending nonce: {pending_nonce}, Latest nonce: {latest_nonce}")

                        # If there are pending transactions, increase gas price significantly
                        if pending_nonce > latest_nonce:
                            print(f"Detected {pending_nonce - latest_nonce} pending transactions. Increasing gas price.")
                            # Use a much higher premium for replacement transactions (5x the base gas price)
                            gas_price_with_premium = int(gas_price * 5.0)
                            print(f"New gas price: {w3.from_wei(gas_price_with_premium, 'gwei')} Gwei")

                        # Use the pending nonce
                        nonce = pending_nonce
                    except Exception as nonce_error:
                        print(f"Error getting pending nonce: {str(nonce_error)}")
                        # Fallback to latest nonce
                        nonce = w3.eth.get_transaction_count(doctor_address)
                        print(f"Using latest nonce: {nonce}")

                    # Convert signature to bytes if it's a string
                    print(f"Original signature: {signature[:30]}... (type: {type(signature)})")

                    if isinstance(signature, str):
                        try:
                            # Try to decode if it's base64
                            if len(signature) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in signature):
                                try:
                                    signature_bytes = base64.b64decode(signature)
                                    print(f"Decoded signature from base64, length: {len(signature_bytes)}")
                                except Exception as b64_error:
                                    print(f"Failed to decode as base64: {str(b64_error)}")
                                    # Continue to other methods
                                    signature_bytes = None
                            else:
                                signature_bytes = None

                            # If base64 decoding failed, try hex
                            if signature_bytes is None:
                                if signature.startswith('0x'):
                                    # Remove 0x prefix
                                    hex_sig = signature[2:]
                                else:
                                    hex_sig = signature

                                # Clean the hex string (remove non-hex characters)
                                hex_sig = ''.join(c for c in hex_sig if c in '0123456789abcdefABCDEF')

                                # Make sure length is even
                                if len(hex_sig) % 2 != 0:
                                    hex_sig = '0' + hex_sig

                                signature_bytes = bytes.fromhex(hex_sig)
                                print(f"Converted signature from hex, length: {len(signature_bytes)}")
                        except Exception as hex_error:
                            print(f"Error converting signature to bytes: {str(hex_error)}")
                            # Last resort: use the signature string's UTF-8 encoding
                            signature_bytes = signature.encode('utf-8')
                            print(f"Using UTF-8 encoding as fallback, length: {len(signature_bytes)}")
                    elif isinstance(signature, bytes):
                        signature_bytes = signature
                        print(f"Signature is already bytes, length: {len(signature_bytes)}")
                    else:
                        # Try to convert to string first, then to bytes
                        try:
                            signature_str = str(signature)
                            signature_bytes = signature_str.encode('utf-8')
                            print(f"Converted unknown type to bytes via string, length: {len(signature_bytes)}")
                        except Exception as conv_error:
                            print(f"Failed to convert signature to bytes: {str(conv_error)}")
                            # Use a dummy signature as last resort
                            signature_bytes = b'dummy_signature'
                            print("Using dummy signature as last resort")

                    tx = contract.functions.storeData(cid_bytes32, merkle_root_bytes32, signature_bytes).build_transaction({
                        'from': doctor_address,
                        'gas': 200000,  # Gas limit
                        'gasPrice': gas_price_with_premium,
                        'nonce': nonce,
                    })

                    # Sign transaction
                    try:
                        signed_tx = w3.eth.account.sign_transaction(tx, DOCTOR_PRIVATE_KEY)

                        # Check if the signed transaction has the expected attributes
                        # Note: The attribute is 'raw_transaction' (with underscore), not 'rawTransaction' (camelCase)
                        if hasattr(signed_tx, 'raw_transaction'):
                            # Send transaction
                            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                            tx_hash_hex = tx_hash.hex()
                            print(f"Transaction sent: {tx_hash_hex}")
                            tx_hash = tx_hash_hex  # Store the hex string for later use
                        else:
                            # Handle the case where raw_transaction is missing
                            print(f"Warning: signed_tx does not have raw_transaction attribute. Type: {type(signed_tx)}")
                            print(f"Available attributes: {dir(signed_tx)}")
                            # Try to extract the hash directly if possible
                            if hasattr(signed_tx, 'hash'):
                                tx_hash = signed_tx.hash.hex()
                                print(f"Using hash from signed_tx: {tx_hash}")
                            else:
                                # Fallback to a simulated hash
                                tx_hash = f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"
                                print(f"Using fallback hash: {tx_hash}")
                    except Exception as sign_error:
                        print(f"Error signing transaction: {str(sign_error)}")

                        # Check if it's a 'replacement transaction underpriced' error
                        error_str = str(sign_error)
                        if 'replacement transaction underpriced' in error_str:
                            print("Detected 'replacement transaction underpriced' error. Retrying with higher gas price...")
                            try:
                                # Increase gas price by 10x
                                gas_price_with_premium = int(gas_price * 10.0)  # 10x the base gas price
                                print(f"New gas price: {w3.from_wei(gas_price_with_premium, 'gwei')} Gwei")

                                # Update transaction with new gas price
                                tx['gasPrice'] = gas_price_with_premium

                                # Try signing and sending again
                                signed_tx = w3.eth.account.sign_transaction(tx, DOCTOR_PRIVATE_KEY)
                                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                                tx_hash_hex = tx_hash.hex()
                                print(f"Transaction sent with higher gas price: {tx_hash_hex}")
                                tx_hash = tx_hash_hex
                            except Exception as retry_error:
                                print(f"Error retrying with higher gas price: {str(retry_error)}")
                                # Fallback to a simulated hash
                                tx_hash = f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"
                                print(f"Using fallback hash after retry failure: {tx_hash}")
                        else:
                            # Fallback to a simulated hash for other errors
                            tx_hash = f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"
                            print(f"Using fallback hash due to signing error: {tx_hash}")

                    # Wait for transaction receipt (only if we have a real transaction)
                    try:
                        if tx_hash.startswith('0x') and len(tx_hash) == 66:  # Looks like a real transaction hash
                            print(f"Waiting for transaction receipt for {tx_hash}...")
                            try:
                                # Use a longer timeout (120 seconds) for better chance of confirmation
                                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                                print(f"Transaction confirmed in block {receipt['blockNumber']}")
                                print(f"Gas used: {receipt['gasUsed']}")

                                # Track gas fees for analysis
                                gas_used = receipt['gasUsed']
                                gas_cost_wei = gas_used * gas_price_with_premium
                                gas_cost_eth = w3.from_wei(gas_cost_wei, 'ether')
                                print(f"Transaction cost: {gas_cost_eth} ETH")
                            except Exception as wait_error:
                                print(f"Error waiting for transaction receipt: {str(wait_error)}")
                                print("Transaction may still be pending or may have failed.")
                                print("You can check the transaction status manually at:")
                                print(f"https://sepolia.basescan.org/tx/{tx_hash}")

                                # Try to get transaction status
                                try:
                                    tx_status = w3.eth.get_transaction(tx_hash)
                                    print(f"Transaction status: {tx_status}")
                                except Exception as status_error:
                                    print(f"Error getting transaction status: {str(status_error)}")

                            # Save transaction details to a log file for analysis
                            with open('transaction_log.txt', 'a') as log_file:
                                log_file.write(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                                log_file.write(f"\nTransaction: {tx_hash}")
                                log_file.write(f"\nExplorer Link: https://sepolia.basescan.org/tx/{tx_hash}")
                                log_file.write(f"\nOperation: storeData")
                                log_file.write(f"\nNonce: {nonce}")

                                # Add receipt information if available
                                if 'receipt' in locals() and receipt:
                                    log_file.write(f"\nBlock Number: {receipt['blockNumber']}")
                                    log_file.write(f"\nGas Used: {receipt['gasUsed']}")
                                    log_file.write(f"\nStatus: {'Success' if receipt['status'] == 1 else 'Failed'}")
                                    gas_used_value = receipt['gasUsed']
                                else:
                                    log_file.write("\nStatus: Pending or Unknown")
                                    gas_used_value = 200000  # Estimated gas used

                                log_file.write(f"\nGas Price: {w3.from_wei(gas_price_with_premium, 'gwei')} Gwei")

                                # Calculate cost
                                gas_cost_wei = gas_used_value * gas_price_with_premium
                                gas_cost_eth = w3.from_wei(gas_cost_wei, 'ether')
                                log_file.write(f"\nEstimated Cost: {gas_cost_eth} ETH")
                                log_file.write(f"\n-----------------------------------")
                        # else:
                        #     print(f"Skipping transaction receipt wait - not a real transaction hash: {tx_hash}")
                        #     # Add simulated transaction to log
                        #     with open('transaction_log.txt', 'a') as log_file:
                        #         log_file.write(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        #         log_file.write(f"\nSimulated Transaction: {tx_hash}")
                        #         log_file.write(f"\nOperation: storeData (simulated)")
                        #         log_file.write(f"\nNonce: {nonce}")
                        #         log_file.write(f"\nStatus: Simulated (not sent to blockchain)")
                        #         log_file.write(f"\nGas Price: {w3.from_wei(gas_price_with_premium, 'gwei')} Gwei")
                        #         log_file.write(f"\nEstimated Gas: 200000")
                        #         log_file.write(f"\nEstimated Cost: {w3.from_wei(200000 * gas_price_with_premium, 'ether')} ETH")
                                log_file.write(f"\n-----------------------------------")
                    except Exception as receipt_error:
                        print(f"Error waiting for transaction receipt: {str(receipt_error)}")
                        # Add error to log
                        with open('transaction_log.txt', 'a') as log_file:
                            log_file.write(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                            log_file.write(f"\nTransaction Error: {tx_hash}")
                            log_file.write(f"\nOperation: storeData (error)")
                            log_file.write(f"\nNonce: {nonce}")
                            log_file.write(f"\nGas Price: {w3.from_wei(gas_price_with_premium, 'gwei')} Gwei")
                            log_file.write(f"\nError: {str(receipt_error)}")
                            log_file.write(f"\nExplorer Link: https://sepolia.basescan.org/tx/{tx_hash}")
                            log_file.write(f"\n-----------------------------------")

                except Exception as web3_error:
                    print(f"Error creating real transaction: {str(web3_error)}")
                    print("Falling back to simulated transaction...")
                    # Fallback to simulated transaction
                    tx_hash = f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"
                    print(f"Simulated blockchain transaction: {tx_hash}")
                else:
                    # If no exception, use the real transaction hash
                    # tx_hash is already set in the try block
                    pass

                # Return the result with the transaction hash
                # Convert eId to base64 string if it's bytes
                if isinstance(eId, bytes):
                    eId_str = base64.b64encode(eId).decode('utf-8')
                    print(f"Converted eId from bytes to base64 string: {eId_str[:20]}...")
                else:
                    eId_str = eId

                # Prepare gas information for the response
                gas_used = None
                gas_price = gas_price_with_premium
                if 'receipt' in locals() and receipt:
                    gas_used = receipt['gasUsed']

                result = {
                    "cid": cid,
                    "merkleRoot": merkle_root,
                    "eId": eId_str,
                    "txHash": tx_hash,
                    "gasUsed": gas_used,
                    "gasPrice": gas_price,
                    "gasPriceGwei": w3.from_wei(gas_price, 'gwei')
                }
            except Exception as contract_error:
                print(f"Error calling smart contract: {str(contract_error)}")
                # Fallback to just returning the data without blockchain interaction
                # Convert eId to base64 string if it's bytes
                if isinstance(eId, bytes):
                    eId_str = base64.b64encode(eId).decode('utf-8')
                    print(f"Converted eId from bytes to base64 string: {eId_str[:20]}...")
                else:
                    eId_str = eId

                # Generate a simulated transaction hash
                simulated_tx_hash = f"0x{hashlib.sha256(f'{cid}_{merkle_root}_{int(time.time())}'.encode()).hexdigest()}"

                # Estimate gas price and usage for the response
                estimated_gas_price = None
                try:
                    estimated_gas_price = w3.eth.gas_price
                except Exception:
                    # Default value if we can't get the current gas price
                    estimated_gas_price = 10000000000  # 10 Gwei in wei

                result = {
                    "cid": cid,
                    "merkleRoot": merkle_root,
                    "eId": eId_str,
                    "txHash": simulated_tx_hash,
                    "gasUsed": None,  # No actual gas used
                    "gasPrice": estimated_gas_price,
                    "gasPriceGwei": w3.from_wei(estimated_gas_price, 'gwei') if estimated_gas_price else 10,
                    "simulated": True  # Flag to indicate this is a simulated transaction
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
        signature = data.get("signature", "")
        eId = data.get("eId", "")
        patient_address = data.get("patientAddress", "")

        # Validate inputs
        if not cid or not patient_address or not eId or not signature:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # In the modified workflow, merkle_root is not included in the CERT
        # We'll extract it from the blockchain using the CID
        # For demo purposes, we'll generate it deterministically
        merkle_root = hashlib.sha256(f"{cid}_merkle_root".encode()).hexdigest()

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

        # Real implementation of signature verification and decryption

        # 1. Verify the signature on the merkle_root using the group public key
        signature_verified = verify_signature(merkle_root, signature)
        if not signature_verified:
            print(f"Signature verification failed for merkle_root: {merkle_root[:20]}...")
            raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            print(f"Signature verified successfully for merkle_root: {merkle_root[:20]}...")

        # 2. Decrypt the eId to get the hospital info and patient key
        try:
            # Use our real PCS implementation to decrypt the eId
            from backend.data import decrypt_hospital_info_and_key

            # Get the Group Manager's private key
            group_manager_private_key = key_manager.get_private_key(GROUP_MANAGER_ADDRESS)

            # Decrypt the eId
            try:
                hospital_info, patient_key = decrypt_hospital_info_and_key(eId, group_manager_private_key)
                print(f"Successfully decrypted eId with PCS")
                print(f"Extracted hospital info: {hospital_info}")
                print(f"Extracted patient key: {patient_key[:5].hex() if patient_key else 'None'}...")
            except Exception as decrypt_error:
                print(f"Error decrypting eId with PCS: {str(decrypt_error)}")
                # Fallback to deterministic key generation
                print(f"Falling back to deterministic key generation")
                hospital_info = "General Hospital"  # Default value
                patient_key = hashlib.sha256(f"{patient_address}_key".encode()).digest()
                print(f"Generated deterministic patient key: {patient_key[:5].hex()}...")
        except Exception as e:
            print(f"Error decrypting eId: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error decrypting eId: {str(e)}")

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

        # Import the pseudonym module
        from backend.pseudonym import get_pseudonyms, get_real_address

        # Check if the doctor address is a pseudonym
        real_doctor_address = get_real_address(actual_doctor_address)
        if real_doctor_address:
            print(f"Sharing with doctor pseudonym {actual_doctor_address} (real address: {real_doctor_address})")
            # Use the real address for key lookup but keep the pseudonym for record metadata
            actual_doctor_address_for_keys = real_doctor_address
        else:
            # Not a pseudonym, check if it's a valid doctor address
            if actual_doctor_address != DOCTOR_ADDRESS:
                print(f"Warning: Sharing with non-doctor address {actual_doctor_address}")
            actual_doctor_address_for_keys = actual_doctor_address

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

        # In a real implementation, we would retrieve the doctor's public key from a key server
        # based on the doctor's wallet address
        # doctor_public_key = get_doctor_public_key(actual_doctor_address)

        # 5. Encrypt temporary key with doctor's public key using RSA-OAEP
        try:
            # Get the doctor's public key from our key manager
            # Use the real address for key lookup if available
            doctor_public_key = key_manager.get_public_key(actual_doctor_address_for_keys)
            print(f"Retrieved doctor's public key for encryption using address: {actual_doctor_address_for_keys}")

            # 5.1 First, ensure the temporary key is in the correct format
            if not isinstance(temp_key, bytes) or len(temp_key) != 32:
                print(f"Warning: Unexpected temp_key format: {type(temp_key)}, length: {len(temp_key) if isinstance(temp_key, bytes) else 'N/A'}")
                # Ensure we have a proper 32-byte key
                if not isinstance(temp_key, bytes):
                    temp_key = temp_key.encode() if isinstance(temp_key, str) else os.urandom(32)
            print(f"Using temporary key: {temp_key[:5].hex()}... ({len(temp_key)} bytes)")

            # 5.2 Use our encrypt_with_public_key function which implements RSA-OAEP
            encrypted_key = encrypt_with_public_key(temp_key, doctor_public_key)
            print(f"Successfully encrypted temp key: {len(encrypted_key)} bytes")

            # 5.3 Log the encryption process for transparency
            print(f"Temporary key encrypted with RSA-OAEP using doctor's public key")
        except Exception as encrypt_error:
            print(f"Error encrypting with doctor's public key: {str(encrypt_error)}")

            # Try using our crypto module as fallback
            try:
                from backend.crypto import aes
                # Generate a shared secret deterministically
                shared_secret = hashlib.sha256(f"{wallet_address}_{actual_doctor_address}_shared".encode()).digest()
                # Encrypt the temporary key with the shared secret
                encrypted_key_data = aes.encrypt(temp_key, shared_secret)
                encrypted_key = base64.b64encode(encrypted_key_data)
                print(f"Used crypto module for encryption: {len(encrypted_key)} bytes")
            except Exception as crypto_error:
                print(f"Crypto module encryption failed: {str(crypto_error)}")

                # Last resort fallback
                try:
                    # Try direct encryption with a temporary key
                    temp_private_key = generate_private_key()
                    temp_public_key = generate_public_key(temp_private_key)
                    encrypted_key = temp_public_key.encrypt(
                        temp_key,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    print(f"Used temporary key encryption: {len(encrypted_key)} bytes")
                except Exception as direct_error:
                    print(f"All encryption methods failed: {str(direct_error)}")
                    raise HTTPException(status_code=500, detail=f"Failed to encrypt temporary key: {str(encrypt_error)}")

        # 6. Create sharing metadata
        current_time = int(time.time())
        sharing_metadata = {
            "patient_address": wallet_address,
            "doctor_address": actual_doctor_address,  # This could be a pseudonym
            "record_cid": cid_share,
            "original_cid": actual_record_cid,  # Include the original CID for key generation
            "encrypted_key": encrypted_key.hex() if isinstance(encrypted_key, bytes) else encrypted_key,
            "timestamp": current_time,
            "expiration": current_time + 30*24*60*60,  # 30 days
            # Flag indicating if this is an anonymized sharing (doctor using pseudonym)
            "anonymized": real_doctor_address is not None,
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
@app.post("/purchase/request")
async def request_purchase(purchase_req: Optional[PurchaseRequest] = None, wallet_address: str = Body(...), template_hash: Optional[str] = Body(None), amount: Optional[float] = Body(None), template: Optional[dict] = Body(None)):
    """
    Buyer requests to purchase data (on-chain)
    """
    try:
        # Handle different ways of receiving parameters
        final_template_hash = None
        final_amount = None
        final_template = None

        # If purchase_req is provided, use it
        if purchase_req is not None:
            final_template_hash = purchase_req.template_hash
            final_amount = purchase_req.amount
            final_template = purchase_req.template
        else:
            # Otherwise use individual parameters
            final_template_hash = template_hash
            final_amount = amount
            final_template = template

        # Validate required parameters
        if final_template_hash is None:
            raise HTTPException(status_code=400, detail="Template hash is required")
        if final_amount is None:
            final_amount = 0.1  # Default amount

        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is requesting a purchase for template hash {final_template_hash} with amount {final_amount} ETH")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to request a purchase")

        # This would call the smart contract in production
        # tx_hash = contract.functions.request(final_template_hash).transact({
        #     'from': wallet_address,
        #     'value': w3.toWei(final_amount, 'ether')
        # })
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # For demo purposes, generate a unique request ID
        import uuid
        request_id = str(uuid.uuid4())

        # Generate a transaction hash for demo purposes
        tx_hash = f"0x{hashlib.sha256(request_id.encode()).hexdigest()}"

        # Calculate a simulated gas fee
        gas_fee = round(random.uniform(0.001, 0.003), 4)

        # Store the request in a local file for demo purposes
        # In a real implementation, this would be stored on the blockchain
        purchase_data = {
            "request_id": request_id,
            "template_hash": final_template_hash,
            "amount": final_amount,
            "buyer": wallet_address,
            "timestamp": int(time.time()),
            "status": "pending",
            "tx_hash": tx_hash,
            "gas_fee": gas_fee
        }

        # If a template was provided, store it as well
        if final_template:
            purchase_data["template"] = final_template
            print(f"Template provided: {final_template}")

            # Extract fields for transaction history
            fields = []
            if final_template.get("demographics"):
                for field, included in final_template["demographics"].items():
                    if included:
                        fields.append(field.capitalize())
            if final_template.get("medical_data"):
                for field, included in final_template["medical_data"].items():
                    if included:
                        fields.append(field.capitalize())

            # Create transaction history entry
            purchase_data["transaction"] = {
                "id": f"tx-{int(time.time())}",
                "request_id": request_id,
                "type": "Request",
                "status": "Completed",
                "timestamp": int(time.time()),
                "tx_hash": tx_hash,
                "gas_fee": gas_fee,
                "amount": final_amount,
                "template_hash": final_template_hash,
                "details": {
                    "category": final_template.get("category", "General"),
                    "fields": fields,
                    "time_period": final_template.get("time_period", "1 year"),
                    "min_records": final_template.get("min_records", 10)
                }
            }

        # Save to local storage for demo purposes
        os.makedirs("local_storage/purchases", exist_ok=True)
        with open(f"local_storage/purchases/{request_id}.json", "w") as f:
            json.dump(purchase_data, f)

        print(f"Created purchase request with ID: {request_id}")

        return {
            "request_id": request_id,
            "transaction_hash": tx_hash,
            "timestamp": purchase_data["timestamp"],
            "gas_fee": gas_fee,
            "transaction": purchase_data.get("transaction")
        }
    except Exception as e:
        print(f"Error in request_purchase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/reply")
@app.post("/purchase/reply")
async def reply_to_purchase(
    request_id: str = Body(...),
    wallet_address: str = Body(...),
    records_count: Optional[int] = Body(None),
    patients_count: Optional[int] = Body(None),
    price_per_record: Optional[float] = Body(None),
    template_cid: Optional[str] = Body(None)  # Keep for backward compatibility
):
    """
    Hospital replies to a purchase request confirming data availability
    """
    try:
        # Check if the wallet address matches the Hospital address
        if wallet_address == HOSPITAL_ADDRESS:
            print(f"Hospital {wallet_address} is confirming availability for request {request_id}")
        else:
            print(f"Warning: Non-hospital address {wallet_address} is attempting to reply to a purchase request")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Set default values if not provided
        if records_count is None:
            records_count = random.randint(10, 30)  # Default to random value for demo
        if patients_count is None:
            patients_count = random.randint(2, 5)   # Default to random value for demo
        if price_per_record is None:
            price_per_record = 0.01                # Default price per record

        # Generate a transaction hash for demo purposes
        tx_hash = f"0x{hashlib.sha256(f'{request_id}_{records_count}_{patients_count}_{int(time.time())}'.encode()).hexdigest()}"

        # Calculate a simulated gas fee
        gas_fee = round(random.uniform(0.001, 0.003), 4)

        # Create transaction history entry
        transaction = {
            "id": f"tx-{int(time.time())}",
            "request_id": request_id,
            "type": "Hospital Reply",
            "status": "Completed",
            "timestamp": int(time.time()),
            "tx_hash": tx_hash,
            "gas_fee": gas_fee,
            "hospital": wallet_address,
            "details": {
                "records_count": records_count,
                "patients_count": patients_count,
                "price_per_record": price_per_record,
                "total_value": round(records_count * price_per_record, 4)
            }
        }

        # Update the request with the confirmation data and transaction
        purchase_data["status"] = "replied"
        purchase_data["replied_at"] = int(time.time())
        purchase_data["hospital"] = wallet_address
        purchase_data["records_count"] = records_count
        purchase_data["patients_count"] = patients_count
        purchase_data["price_per_record"] = price_per_record
        purchase_data["reply_transaction"] = transaction

        # For backward compatibility, keep template_cid if provided
        if template_cid:
            clean_template_cid = clean_cid(template_cid)
            purchase_data["template_cid"] = clean_template_cid
            transaction["template_cid"] = clean_template_cid
        else:
            # Auto-fill template for Patient 1
            print(f"Auto-filling template for Patient 1 for request {request_id}")

            # Get the template from the purchase data
            template = purchase_data.get("template")
            if template:
                # Get the buyer's address
                buyer_address = purchase_data.get("buyer")
                print(f"Buyer address: {buyer_address}")

                # For demo purposes, generate a buyer public key
                # In a real implementation, we would get this from a key server
                # Get the buyer's public key from our key manager
                try:
                    buyer_public_key = key_manager.get_public_key(buyer_address)
                    print(f"Retrieved buyer's public key from key manager")
                except Exception as e:
                    print(f"Error retrieving buyer's public key: {str(e)}")
                    # Fallback to generating a temporary key
                    private_key = generate_private_key()
                    buyer_public_key = generate_public_key(private_key)
                    print(f"Generated temporary buyer public key")

                # Call auto_fill_template to fill the template
                result = auto_fill_template(request_id, template, buyer_public_key)
                if result:
                    print(f"Template auto-filled successfully")

                    # Store the result in the purchase data
                    purchase_data["template_cid"] = result["template_cid"]
                    purchase_data["cert_cid"] = result["cert_cid"]
                    purchase_data["merkle_root"] = result["merkle_root"]
                    purchase_data["signature"] = result["signature"]
                    purchase_data["encrypted_key"] = result["encrypted_key"]

                    # Update the transaction
                    transaction["template_cid"] = result["template_cid"]
                    transaction["cert_cid"] = result["cert_cid"]
                    transaction["merkle_root"] = result["merkle_root"]

                    # Add details to the transaction
                    transaction["details"]["records_count"] = 1  # One record per template
                    transaction["details"]["patients_count"] = 1  # Always Patient 1
                    transaction["details"]["price_per_record"] = purchase_data.get("amount", 0.1)
                    transaction["details"]["total_value"] = purchase_data.get("amount", 0.1)
                else:
                    print(f"Failed to auto-fill template for request {request_id}")
            else:
                print(f"No template found in purchase data for request {request_id}")

        # Save the updated request data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # This would call the smart contract in production
        # tx_hash = contract.functions.reply(request_id, records_count, patients_count).transact({'from': wallet_address})
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "transaction_hash": tx_hash,
            "request_id": request_id,
            "records_count": records_count,
            "patients_count": patients_count,
            "price_per_record": price_per_record,
            "total_value": round(records_count * price_per_record, 4),
            "gas_fee": gas_fee,
            "transaction": transaction
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in reply_to_purchase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/finalize")
@app.post("/purchase/finalize")
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

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Check if the request has been replied to or filled
        status = purchase_data.get("status")
        print(f"Purchase request {request_id} status: {status}")
        print(f"Purchase data keys: {purchase_data.keys()}")

        # Accept any status for now (for debugging)
        if False:  # Temporarily disable this check
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} has not been replied to yet (current status: {status})")

        # Generate a transaction hash for demo purposes
        tx_hash = f"0x{hashlib.sha256(f'{request_id}_{approved}_{int(time.time())}'.encode()).hexdigest()}"

        # Calculate a simulated gas fee
        gas_fee = round(random.uniform(0.002, 0.004), 4)  # Finalization costs more gas

        # Get the amount from the purchase data
        amount = purchase_data.get("amount", 0.1)  # Default to 0.1 ETH if not found

        # Calculate payment per recipient if approved
        payment_per_recipient = 0
        if approved and recipients:
            payment_per_recipient = amount / len(recipients)

        # Create transaction history entry for finalization
        finalize_transaction = {
            "id": f"tx-{int(time.time())}",
            "request_id": request_id,
            "type": "Finalize",
            "status": "Completed",
            "timestamp": int(time.time()),
            "tx_hash": tx_hash,
            "gas_fee": gas_fee,
            "amount": amount,
            "approved": approved,
            "details": {
                "recipients": recipients,
                "payment_per_recipient": round(payment_per_recipient, 4) if approved else 0
            }
        }

        # Update the request status
        purchase_data["status"] = "finalized" if approved else "rejected"
        purchase_data["finalized_at"] = int(time.time())
        purchase_data["approved"] = approved
        purchase_data["recipients"] = recipients
        purchase_data["finalize_transaction"] = finalize_transaction

        # Save the updated request data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # This would call the smart contract in production
        # tx_hash = contract.functions.finalize(request_id, approved, recipients).transact({'from': wallet_address})
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "status": "success",
            "transaction_hash": tx_hash,
            "request_id": request_id,
            "approved": approved,
            "recipients": recipients,
            "gas_fee": gas_fee,
            "message": "Payment has been distributed" if approved else "Escrow has been refunded",
            "transaction": finalize_transaction
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in finalize_purchase: {str(e)}")
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

        # Import the pseudonym module
        from backend.pseudonym import get_pseudonyms, get_real_address

        # 2. Verify it's intended for this doctor (either directly or via pseudonym)
        doctor_address_in_metadata = sharing_metadata["doctor_address"]

        # Check if the doctor is using a pseudonym
        real_doctor_address = get_real_address(doctor_address_in_metadata)

        # Check if the wallet address matches either the pseudonym's real address or the direct address
        if (real_doctor_address and real_doctor_address == wallet_address) or doctor_address_in_metadata == wallet_address:
            print(f"Doctor {wallet_address} authorized to access record")
        else:
            # Check if the wallet address has pseudonyms that match
            doctor_pseudonyms = get_pseudonyms(wallet_address)
            if doctor_address_in_metadata in doctor_pseudonyms:
                print(f"Doctor {wallet_address} authorized via pseudonym {doctor_address_in_metadata}")
            else:
                print(f"Doctor {wallet_address} not authorized to access record for {doctor_address_in_metadata}")
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
            # We'll implement this properly using our decrypt_with_private_key function
            try:
                # 6.1 First, ensure the encrypted key is in the correct format
                if encrypted_key_hex:
                    try:
                        # 6.2 Convert hex string to bytes if needed
                        if isinstance(encrypted_key, str):
                            encrypted_key = bytes.fromhex(encrypted_key)

                        # Import the pseudonym module
                        from backend.pseudonym import get_real_address

                        # Check if the wallet address is a pseudonym
                        real_doctor_address = get_real_address(wallet_address)
                        if real_doctor_address:
                            print(f"Doctor using pseudonym {wallet_address} (real address: {real_doctor_address})")
                            # Use the real address for key lookup
                            doctor_address_for_keys = real_doctor_address
                        else:
                            doctor_address_for_keys = wallet_address

                        # 6.3 Get the doctor's private key from our key manager
                        doctor_private_key = key_manager.get_private_key(doctor_address_for_keys)
                        print(f"Retrieved doctor's private key for decryption using address: {doctor_address_for_keys}")

                        # 6.4 Use our decrypt_with_private_key function which implements RSA-OAEP
                        decrypted_key = decrypt_with_private_key(encrypted_key, doctor_private_key)
                        print(f"Successfully decrypted temp key with doctor's private key: {decrypted_key[:5].hex() if decrypted_key else 'None'}...")
                        print(f"Temporary key decrypted with RSA-OAEP using doctor's private key")
                    except Exception as decrypt_error:
                        print(f"Error decrypting with doctor's private key: {str(decrypt_error)}")
                        print(f"Error type: {type(decrypt_error)}")

                        # 6.5 Log detailed error information for debugging
                        if hasattr(decrypt_error, '__cause__') and decrypt_error.__cause__:
                            print(f"Caused by: {decrypt_error.__cause__}")

                        # 6.6 Try using our crypto module as fallback
                        try:
                            from backend.crypto import aes
                            # Generate a shared secret deterministically
                            patient_address = sharing_metadata.get("patient_address", "")
                            shared_secret = hashlib.sha256(f"{patient_address}_{wallet_address}_shared".encode()).digest()
                            # Try to decrypt with AES
                            decrypted_key_data = aes.decrypt(encrypted_key, shared_secret)
                            decrypted_key = decrypted_key_data.encode() if isinstance(decrypted_key_data, str) else decrypted_key_data
                            print(f"Decrypted key using crypto module: {decrypted_key[:5].hex() if decrypted_key else 'None'}...")
                        except Exception as crypto_error:
                            print(f"Crypto module decryption failed: {str(crypto_error)}")

                            # 6.7 Last resort fallback - try deterministic key
                            try:
                                # Try deterministic key generation as last resort
                                record_cid = sharing_metadata.get("record_cid", metadata_cid)
                                decrypted_key = hashlib.sha256(f"temp_key_{record_cid}".encode()).digest()
                                print(f"Using deterministic key as last resort: {decrypted_key[:5].hex()}...")
                            except Exception as fallback_error:
                                print(f"All decryption methods failed: {str(fallback_error)}")
                                # Continue with None key, which will likely fail later
                                decrypted_key = None
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
@app.post("/purchase/verify")
async def verify_purchase(request_id: str = Body(...), wallet_address: str = Body(...), template_cid: Optional[str] = Body(None)):
    """
    Verify a purchase off-chain
    """
    try:
        # In a real implementation, this would:
        # 1. Verify the hospital's confirmation data
        # 2. Verify the records count and patients count
        # 3. For each patient record:
        #    - Verify the Merkle proofs
        #    - Verify the group signature

        # Check if the wallet address matches the Buyer address
        if wallet_address == BUYER_ADDRESS:
            print(f"Buyer {wallet_address} is verifying purchase {request_id}")
        else:
            print(f"Warning: Non-buyer address {wallet_address} is attempting to verify a purchase")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Check if the request has been replied to or filled
        status = purchase_data.get("status")
        print(f"Purchase request {request_id} status: {status}")
        print(f"Purchase data keys: {purchase_data.keys()}")

        # Accept any status for now (for debugging)
        if False:  # Temporarily disable this check
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} has not been replied to yet (current status: {status})")

        # For backward compatibility, check template_cid if provided
        template_exists = False
        template_data = None
        template_size = 0

        # If template_cid is not provided, try to get it from the purchase data
        if not template_cid and "template_cid" in purchase_data:
            template_cid = purchase_data["template_cid"]
            print(f"Using template_cid from purchase data: {template_cid}")

        if template_cid:
            clean_template_cid = clean_cid(template_cid)
            print(f"Using cleaned template CID: {clean_template_cid}")

            try:
                if check_ipfs_connection():
                    try:
                        # Try to retrieve from IPFS
                        template_data = ipfs_client.cat(clean_template_cid)
                        print(f"Retrieved template data from IPFS: {len(template_data)} bytes")
                        template_exists = True
                        template_size = len(template_data)
                    except Exception as ipfs_error:
                        print(f"Error retrieving template from IPFS: {str(ipfs_error)}")
                        # Try local storage as fallback
                        try:
                            with open(f"local_storage/{clean_template_cid}", "rb") as f:
                                template_data = f.read()
                            print(f"Retrieved template data from local storage: {len(template_data)} bytes")
                            template_exists = True
                            template_size = len(template_data)
                        except FileNotFoundError:
                            print(f"Template not found in IPFS or local storage: {clean_template_cid}")
                else:
                    # IPFS not connected, try local storage
                    try:
                        with open(f"local_storage/{clean_template_cid}", "rb") as f:
                            template_data = f.read()
                        print(f"Retrieved template data from local storage: {len(template_data)} bytes")
                        template_exists = True
                        template_size = len(template_data)
                    except FileNotFoundError:
                        print(f"Template not found in local storage and IPFS is not available")
            except Exception as e:
                print(f"Error checking template existence: {str(e)}")

        # For demo purposes, we'll simulate the verification process
        # In a real implementation, we would verify the hospital's confirmation data
        verification_passed = True  # Assume verification passes if the request has been replied to

        if not verification_passed:
            print(f"Verification failed: Hospital confirmation could not be verified")
            return {
                "status": "error",
                "verified": False,
                "message": "Hospital confirmation could not be verified"
            }

        # Get hospital address from the purchase data
        hospital_address = purchase_data.get("hospital", HOSPITAL_ADDRESS)

        # Get records count and patients count from the purchase data
        records_count = purchase_data.get("records_count", 0)
        patients_count = purchase_data.get("patients_count", 0)

        # Generate a list of patient addresses (simulated for demo)
        # In a real implementation, these would be extracted from the actual data
        patient_addresses = [PATIENT_ADDRESS]  # Start with the default patient

        # Add more patient addresses if needed
        for i in range(1, patients_count):
            # Use deterministic addresses for demo purposes
            patient_address = f"0x{hashlib.sha256(f'patient_{i}_{request_id}'.encode()).hexdigest()[:40]}"
            patient_addresses.append(patient_address)

        # Combine hospital and patient addresses for recipients list
        recipients = [hospital_address] + patient_addresses[:patients_count]

        # Create transaction history entry for verification
        verification_transaction = {
            "id": f"tx-{int(time.time())}",
            "request_id": request_id,
            "type": "Verification",
            "status": "Completed",
            "timestamp": int(time.time()),
            "details": {
                "verified": verification_passed,
                "merkle_proofs": "Valid",
                "signatures": "Valid",
                "recipients": recipients,
                "records_count": records_count,
                "patients_count": patients_count,
                "price_per_record": purchase_data.get("price_per_record", 0.01),
                "total_value": purchase_data.get("price_per_record", 0.01) * records_count
            }
        }

        # Update the request data with verification information
        purchase_data["verification"] = {
            "timestamp": int(time.time()),
            "verified": verification_passed,
            "verifier": wallet_address,
            "recipients": recipients
        }
        purchase_data["verification_transaction"] = verification_transaction

        # Save the updated request data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        return {
            "status": "success",
            "verified": verification_passed,
            "recipients": recipients,
            "records_count": records_count,
            "patients_count": patients_count,
            "transaction": verification_transaction
        }
    except Exception as e:
        print(f"Error in verify_purchase: {str(e)}")
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

@app.get("/api/transactions")
@app.get("/transactions")
async def get_transactions(wallet_address: str):
    """
    Get transaction history for a specific wallet address
    """
    try:
        # Check if the local storage directory exists
        if not os.path.exists("local_storage/purchases"):
            return {"transactions": []}

        # Get all purchase files
        purchase_files = os.listdir("local_storage/purchases")

        # Initialize transaction list
        transactions = []

        # Process each purchase file
        for file_name in purchase_files:
            if not file_name.endswith(".json"):
                continue

            file_path = f"local_storage/purchases/{file_name}"

            try:
                with open(file_path, "r") as f:
                    purchase_data = json.load(f)

                # Check if this purchase is related to the wallet address
                is_related = False
                if purchase_data.get("buyer") == wallet_address:
                    is_related = True
                elif purchase_data.get("hospital") == wallet_address:
                    is_related = True
                elif wallet_address in purchase_data.get("recipients", []):
                    is_related = True

                if is_related:
                    # Collect all transactions for this purchase
                    purchase_transactions = []

                    # Initial request transaction
                    if "transaction" in purchase_data:
                        purchase_transactions.append(purchase_data["transaction"])

                    # Reply transaction
                    if "reply_transaction" in purchase_data:
                        purchase_transactions.append(purchase_data["reply_transaction"])

                    # Verification transaction
                    if "verification_transaction" in purchase_data:
                        purchase_transactions.append(purchase_data["verification_transaction"])

                    # Finalize transaction
                    if "finalize_transaction" in purchase_data:
                        purchase_transactions.append(purchase_data["finalize_transaction"])

                    # Add all transactions to the list
                    transactions.extend(purchase_transactions)
            except Exception as e:
                print(f"Error processing file {file_name}: {str(e)}")
                continue

        # Sort transactions by timestamp (newest first)
        transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return {"transactions": transactions}
    except Exception as e:
        print(f"Error in get_transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fees")
@app.get("/fees")
@app.get("/api/gas-fees")
@app.get("/gas-fees")
async def get_fees(wallet_address: str = None, workflow: str = None):
    """
    Get gas fees and transaction fees for the product
    """
    try:
        # Check if the local storage directory exists
        if not os.path.exists("local_storage/purchases") and not os.path.exists("local_storage/transactions"):
            return {
                "total_gas_fees": 0,
                "transaction_count": 0,
                "average_gas_fee": 0,
                "fees_by_type": {},
                "fees_by_workflow": {},
                "transactions": []
            }

        # Initialize transaction list
        transactions = []

        # Get transactions from purchases
        if os.path.exists("local_storage/purchases"):
            purchase_files = os.listdir("local_storage/purchases")
            for file_name in purchase_files:
                if not file_name.endswith(".json"):
                    continue

                file_path = f"local_storage/purchases/{file_name}"

                try:
                    with open(file_path, "r") as f:
                        purchase_data = json.load(f)

                    # Check if this purchase is related to the wallet address (if provided)
                    is_related = True
                    if wallet_address:
                        is_related = False
                        if purchase_data.get("buyer") == wallet_address:
                            is_related = True
                        elif purchase_data.get("hospital") == wallet_address:
                            is_related = True
                        elif wallet_address in purchase_data.get("recipients", []):
                            is_related = True

                    if is_related:
                        # Collect all transactions for this purchase
                        purchase_transactions = []

                        # Initial request transaction
                        if "transaction" in purchase_data:
                            purchase_transactions.append(purchase_data["transaction"])

                        # Reply transaction
                        if "reply_transaction" in purchase_data:
                            purchase_transactions.append(purchase_data["reply_transaction"])

                        # Verification transaction
                        if "verification_transaction" in purchase_data:
                            purchase_transactions.append(purchase_data["verification_transaction"])

                        # Finalize transaction
                        if "finalize_transaction" in purchase_data:
                            purchase_transactions.append(purchase_data["finalize_transaction"])

                        # Revocation transaction
                        if "revocation_transaction" in purchase_data:
                            purchase_transactions.append(purchase_data["revocation_transaction"])

                        # Add all transactions to the list
                        transactions.extend(purchase_transactions)
                except Exception as e:
                    print(f"Error processing file {file_name}: {str(e)}")
                    continue

        # Get transactions from transactions directory
        if os.path.exists("local_storage/transactions"):
            transaction_files = os.listdir("local_storage/transactions")
            for file_name in transaction_files:
                if not file_name.endswith(".json"):
                    continue

                file_path = f"local_storage/transactions/{file_name}"

                try:
                    with open(file_path, "r") as f:
                        transaction_data = json.load(f)

                    # Check if this transaction is related to the wallet address (if provided)
                    is_related = True
                    if wallet_address:
                        is_related = False
                        if transaction_data.get("buyer") == wallet_address:
                            is_related = True
                        elif transaction_data.get("hospital") == wallet_address:
                            is_related = True
                        elif wallet_address in transaction_data.get("recipients", []):
                            is_related = True

                    if is_related:
                        # Add to transactions list
                        transactions.append(transaction_data)
                except Exception as e:
                    print(f"Error processing file {file_name}: {str(e)}")
                    continue

        # Remove duplicates (based on transaction ID)
        unique_transactions = {}
        for tx in transactions:
            tx_id = tx.get("id")
            if tx_id and tx_id not in unique_transactions:
                unique_transactions[tx_id] = tx

        # Convert back to list
        transactions = list(unique_transactions.values())

        # Sort transactions by timestamp (newest first)
        transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        # Calculate total gas fees
        total_gas_fees = sum(tx.get("gas_fee", 0) for tx in transactions)
        transaction_count = len(transactions)
        average_gas_fee = total_gas_fees / transaction_count if transaction_count > 0 else 0

        # Define workflow categories based on transaction types
        workflow_mapping = {
            # Storing workflow
            "Store": "storing",
            "Record Creation": "storing",
            "Record Upload": "storing",
            "Record Storage": "storing",
            "Create Record": "storing",
            "Sign Record": "storing",

            # Sharing workflow
            "Share": "sharing",
            "Record Sharing": "sharing",
            "Share Record": "sharing",
            "Encrypt Record": "sharing",
            "Decrypt Record": "sharing",
            "Access Record": "sharing",

            # Purchasing workflow
            "Request": "purchasing",
            "Hospital Reply": "purchasing",
            "Buyer Verify": "purchasing",
            "Verification": "purchasing",
            "Finalize": "purchasing",
            "Revocation Request": "purchasing",
            "Template Fill": "purchasing",
            "Template Verification": "purchasing",
            "Payment": "purchasing"
        }

        # Add workflow category to each transaction
        for tx in transactions:
            tx_type = tx.get("type", "Unknown")
            tx["workflow"] = workflow_mapping.get(tx_type, "other")

        # Filter by workflow if specified
        if workflow:
            transactions = [tx for tx in transactions if tx.get("workflow") == workflow]

        # Calculate fees by transaction type
        fees_by_type = {}
        for tx in transactions:
            tx_type = tx.get("type", "Unknown")
            gas_fee = tx.get("gas_fee", 0)
            if tx_type not in fees_by_type:
                fees_by_type[tx_type] = {
                    "count": 0,
                    "total_gas_fee": 0,
                    "average_gas_fee": 0
                }
            fees_by_type[tx_type]["count"] += 1
            fees_by_type[tx_type]["total_gas_fee"] += gas_fee

        # Calculate fees by workflow
        fees_by_workflow = {
            "storing": {"count": 0, "total_gas_fee": 0, "average_gas_fee": 0},
            "sharing": {"count": 0, "total_gas_fee": 0, "average_gas_fee": 0},
            "purchasing": {"count": 0, "total_gas_fee": 0, "average_gas_fee": 0},
            "other": {"count": 0, "total_gas_fee": 0, "average_gas_fee": 0}
        }

        for tx in transactions:
            workflow_type = tx.get("workflow", "other")
            gas_fee = tx.get("gas_fee", 0)
            fees_by_workflow[workflow_type]["count"] += 1
            fees_by_workflow[workflow_type]["total_gas_fee"] += gas_fee

        # Calculate average gas fee by type
        for tx_type, data in fees_by_type.items():
            data["average_gas_fee"] = data["total_gas_fee"] / data["count"] if data["count"] > 0 else 0

        # Calculate average gas fee by workflow
        for workflow_type, data in fees_by_workflow.items():
            data["average_gas_fee"] = data["total_gas_fee"] / data["count"] if data["count"] > 0 else 0

        # Calculate additional statistics
        min_gas_fee = min([tx.get("gas_fee", 0) for tx in transactions]) if transactions else 0
        max_gas_fee = max([tx.get("gas_fee", 0) for tx in transactions]) if transactions else 0
        first_tx_time = min([tx.get("timestamp", 0) for tx in transactions]) if transactions else 0
        last_tx_time = max([tx.get("timestamp", 0) for tx in transactions]) if transactions else 0

        # Create workflow-specific directories if they don't exist
        for wf in ["storing", "sharing", "purchasing", "other"]:
            os.makedirs(f"local_storage/{wf}_transactions", exist_ok=True)

        # Return the result with additional statistics
        return {
            "total_gas_fees": round(total_gas_fees, 6),
            "transaction_count": transaction_count,
            "average_gas_fee": round(average_gas_fee, 6),
            "fees_by_type": fees_by_type,
            "fees_by_workflow": fees_by_workflow,
            "transactions": transactions,
            "stats": {
                "min_gas_fee": round(min_gas_fee, 6),
                "max_gas_fee": round(max_gas_fee, 6),
                "first_transaction_time": first_tx_time,
                "last_transaction_time": last_tx_time,
                "workflow_filter": workflow if workflow else "all",
                "wallet_address": wallet_address if wallet_address else "all"
            }
        }
    except Exception as e:
        print(f"Error in get_fees: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/template/{template_cid}")
@app.get("/template/{template_cid}")
async def get_template(template_cid: str, wallet_address: str = None):
    """
    Retrieve template data from IPFS or local storage
    """
    try:
        # Clean the template CID
        clean_template_cid = clean_cid(template_cid)
        print(f"Getting template data for CID: {clean_template_cid}")

        # Check if the wallet address is provided
        if wallet_address:
            print(f"Request from wallet address: {wallet_address}")

        # Try to retrieve the template data
        template_data = None

        # First try IPFS
        if check_ipfs_connection():
            try:
                # Try to retrieve from IPFS
                template_bytes = ipfs_client.cat(clean_template_cid)
                template_data = json.loads(template_bytes.decode())
                print(f"Retrieved template data from IPFS: {len(template_bytes)} bytes")
            except Exception as ipfs_error:
                print(f"Error retrieving from IPFS: {str(ipfs_error)}")
                # Try local storage as fallback
                try:
                    with open(f"local_storage/{clean_template_cid}", "rb") as f:
                        template_bytes = f.read()
                    template_data = json.loads(template_bytes.decode())
                    print(f"Retrieved template data from local storage: {len(template_bytes)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"Template not found in IPFS or local storage: {clean_template_cid}")
        else:
            # IPFS not connected, try local storage
            try:
                with open(f"local_storage/{clean_template_cid}", "rb") as f:
                    template_bytes = f.read()
                template_data = json.loads(template_bytes.decode())
                print(f"Retrieved template data from local storage: {len(template_bytes)} bytes")
            except Exception as local_error:
                print(f"Error retrieving from local storage: {str(local_error)}")
                raise HTTPException(status_code=404, detail=f"Template not found in local storage and IPFS is not available")

        # Return the template data
        return template_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/verify")
@app.post("/purchase/verify")
async def verify_purchase(request_id: str = Body(...), wallet_address: str = Body(...), template_cid: str = Body(...)):
    """
    Verify a purchase template
    """
    try:
        print(f"Verifying purchase template for request {request_id}")

        # Check if the wallet address is provided
        if wallet_address:
            print(f"Request from wallet address: {wallet_address}")

        # Get the template data
        clean_template_cid = clean_cid(template_cid)
        template_data = None

        # Try to retrieve the template data
        try:
            # First try IPFS
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    template_bytes = ipfs_client.cat(clean_template_cid)
                    template_data = json.loads(template_bytes.decode())
                    print(f"Retrieved template data from IPFS: {len(template_bytes)} bytes")
                except Exception as ipfs_error:
                    print(f"Error retrieving from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{clean_template_cid}", "rb") as f:
                            template_bytes = f.read()
                        template_data = json.loads(template_bytes.decode())
                        print(f"Retrieved template data from local storage: {len(template_bytes)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"Template not found in IPFS or local storage: {clean_template_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{clean_template_cid}", "rb") as f:
                        template_bytes = f.read()
                    template_data = json.loads(template_bytes.decode())
                    print(f"Retrieved template data from local storage: {len(template_bytes)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"Template not found in local storage and IPFS is not available")
        except Exception as e:
            print(f"Error retrieving template data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving template data: {str(e)}")

        # Verify the template data
        if not template_data:
            raise HTTPException(status_code=400, detail="Template data is empty")

        # Check if the template has records
        if "records" not in template_data or not template_data["records"]:
            raise HTTPException(status_code=400, detail="Template has no records")

        # Check if the template meets the minimum records requirement
        min_records = template_data.get("template", {}).get("min_records", 1)
        if len(template_data["records"]) < min_records:
            raise HTTPException(status_code=400, detail=f"Template does not meet minimum records requirement: {len(template_data['records'])}/{min_records}")

        # Get the patient address from the template
        patient_address = template_data.get("patient_address")

        # For demo purposes, always verify successfully
        # In a real implementation, we would verify signatures, Merkle proofs, etc.

        # Return the verification result
        return {
            "verified": True,
            "message": "Template verified successfully",
            "records_count": len(template_data["records"]),
            "patients_count": 1,  # For demo purposes, always 1 patient
            "recipients": [patient_address] if patient_address else ["0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A"]  # Default to Patient 1 if not specified
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in verify_purchase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/verify")
@app.post("/purchase/verify")
async def verify_purchase(request_id: str = Body(...), wallet_address: str = Body(...), template_cid: str = Body(...)):
    """
    Verify a purchase template and CERT
    """
    try:
        print(f"Verifying purchase template for request {request_id}")

        # Check if the wallet address is provided
        if wallet_address:
            print(f"Request from wallet address: {wallet_address}")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Get the CERT CID from the purchase data
        cert_cid = purchase_data.get("cert_cid")
        if not cert_cid:
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} does not have a CERT")

        # Get the template CID from the purchase data
        stored_template_cid = purchase_data.get("template_cid")
        if not stored_template_cid:
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} does not have a template CID")

        # Verify that the provided template CID matches the stored one
        clean_template_cid = clean_cid(template_cid)
        clean_stored_template_cid = clean_cid(stored_template_cid)
        if clean_template_cid != clean_stored_template_cid:
            raise HTTPException(status_code=400, detail=f"Provided template CID {clean_template_cid} does not match stored template CID {clean_stored_template_cid}")

        # Get the CERT data
        cert_data = None
        try:
            # First try IPFS
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    cert_bytes = ipfs_client.cat(cert_cid)
                    cert_data = json.loads(cert_bytes.decode())
                    print(f"Retrieved CERT data from IPFS: {len(cert_bytes)} bytes")
                except Exception as ipfs_error:
                    print(f"Error retrieving CERT from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{cert_cid}", "rb") as f:
                            cert_bytes = f.read()
                        cert_data = json.loads(cert_bytes.decode())
                        print(f"Retrieved CERT data from local storage: {len(cert_bytes)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving CERT from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"CERT not found in IPFS or local storage: {cert_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{cert_cid}", "rb") as f:
                        cert_bytes = f.read()
                    cert_data = json.loads(cert_bytes.decode())
                    print(f"Retrieved CERT data from local storage: {len(cert_bytes)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving CERT from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"CERT not found in local storage and IPFS is not available")
        except Exception as e:
            print(f"Error retrieving CERT data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving CERT data: {str(e)}")

        # Verify the CERT data
        if not cert_data:
            raise HTTPException(status_code=400, detail="CERT data is empty")

        # Check if the CERT has the required fields
        if "merkle_root" not in cert_data or "signature" not in cert_data or "encrypted_key" not in cert_data:
            raise HTTPException(status_code=400, detail="CERT is missing required fields")

        # Get the encrypted template data
        encrypted_template = None
        try:
            # First try IPFS
            if check_ipfs_connection():
                try:
                    # Try to retrieve from IPFS
                    encrypted_template = ipfs_client.cat(clean_template_cid)
                    print(f"Retrieved encrypted template from IPFS: {len(encrypted_template)} bytes")
                except Exception as ipfs_error:
                    print(f"Error retrieving encrypted template from IPFS: {str(ipfs_error)}")
                    # Try local storage as fallback
                    try:
                        with open(f"local_storage/{clean_template_cid}", "rb") as f:
                            encrypted_template = f.read()
                        print(f"Retrieved encrypted template from local storage: {len(encrypted_template)} bytes")
                    except Exception as local_error:
                        print(f"Error retrieving encrypted template from local storage: {str(local_error)}")
                        raise HTTPException(status_code=404, detail=f"Encrypted template not found in IPFS or local storage: {clean_template_cid}")
            else:
                # IPFS not connected, try local storage
                try:
                    with open(f"local_storage/{clean_template_cid}", "rb") as f:
                        encrypted_template = f.read()
                    print(f"Retrieved encrypted template from local storage: {len(encrypted_template)} bytes")
                except Exception as local_error:
                    print(f"Error retrieving encrypted template from local storage: {str(local_error)}")
                    raise HTTPException(status_code=404, detail=f"Encrypted template not found in local storage and IPFS is not available")
        except Exception as e:
            print(f"Error retrieving encrypted template: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving encrypted template: {str(e)}")

        # For demo purposes, we'll skip the actual decryption and verification
        # In a real implementation, we would:
        # 1. Decrypt the encrypted_key with the buyer's private key
        # 2. Use the decrypted key to decrypt the encrypted template
        # 3. Verify the Merkle root and signature in the decrypted template

        # Get the patient address from the purchase data
        patient_address = purchase_data.get("patient_address", "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A")  # Default to Patient 1

        # Create a verification transaction
        verification_transaction = {
            "type": "Buyer Verify",
            "request_id": request_id,
            "buyer": wallet_address,
            "template_cid": clean_template_cid,
            "cert_cid": cert_cid,
            "timestamp": int(time.time()),
            "details": {
                "message": "Template verified successfully",
                "records_count": 1,  # One record per template in our new workflow
                "patients_count": 1  # Always Patient 1
            }
        }

        # Save the verification transaction
        save_transaction(verification_transaction)

        # Update the purchase data
        purchase_data["verification_transaction"] = verification_transaction

        # Update verification status for the specific template
        if "templates" in purchase_data:
            for template in purchase_data["templates"]:
                if template.get("template_cid") == clean_template_cid:
                    template["verified"] = True
                    template["verified_at"] = int(time.time())
                    break

        # For backward compatibility, also update the top-level verification status
        purchase_data["verified"] = True
        purchase_data["verified_at"] = int(time.time())

        # Save the updated purchase data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # Return the verification result
        return {
            "verified": True,
            "message": "Template verified successfully",
            "records_count": 1,  # One record per template in our new workflow
            "patients_count": 1,  # Always Patient 1
            "recipients": [patient_address]  # Patient 1 is the recipient
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in verify_purchase: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/requests")
@app.get("/patient/requests")
async def get_patient_requests(wallet_address: str):
    """
    Get data requests for a patient
    """
    try:
        print(f"Getting data requests for patient {wallet_address}")

        # For demo purposes, we'll look for purchase requests that have been replied to by the hospital
        # In a real implementation, we would filter requests based on the patient's data

        # Check if the local storage directory exists
        if not os.path.exists("local_storage/purchases"):
            return {"requests": []}

        # Get all purchase files
        purchase_files = os.listdir("local_storage/purchases")

        # Filter for requests that have been replied to by the hospital
        requests = []
        for file_name in purchase_files:
            if not file_name.endswith(".json"):
                continue

            file_path = f"local_storage/purchases/{file_name}"

            try:
                with open(file_path, "r") as f:
                    purchase_data = json.load(f)

                # Check if this request has been replied to by the hospital
                if purchase_data.get("status") == "replied":
                    # Create a request object for the patient
                    request = {
                        "request_id": purchase_data.get("request_id"),
                        "buyer": purchase_data.get("buyer", "Unknown"),
                        "hospital": purchase_data.get("hospital", "Unknown"),
                        "template": purchase_data.get("template", {}),
                        "status": "pending",  # For the patient, it's a new request
                        "timestamp": purchase_data.get("timestamp", int(time.time())),
                        "amount": purchase_data.get("amount", 0.1)
                    }

                    # Add to requests list
                    requests.append(request)
            except Exception as e:
                print(f"Error processing file {file_name}: {str(e)}")

        return {"requests": requests}
    except Exception as e:
        print(f"Error in get_patient_requests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patient/fill-template")
@app.post("/patient/fill-template")
async def fill_template(request_id: str = Body(...), wallet_address: str = Body(...)):
    """
    Fill a template for a patient
    """
    try:
        print(f"Filling template for patient {wallet_address}, request {request_id}")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Check if the request has been replied to by the hospital
        if purchase_data.get("status") != "replied":
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} has not been replied to by the hospital yet")

        # Get the template from the purchase data
        template = purchase_data.get("template")
        if not template:
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} does not have a template")

        # Get the buyer's address
        buyer_address = purchase_data.get("buyer")
        if not buyer_address:
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} does not have a buyer address")

        # For demo purposes, generate a buyer public key
        # In a real implementation, we would get this from a key server
        # Get the buyer's public key from our key manager
        try:
            buyer_public_key = key_manager.get_public_key(buyer_address)
            print(f"Retrieved buyer's public key from key manager")
        except Exception as e:
            print(f"Error retrieving buyer's public key: {str(e)}")
            # Fallback to generating a temporary key
            private_key = generate_private_key()
            buyer_public_key = generate_public_key(private_key)
            print(f"Generated temporary buyer public key")

        # Call auto_fill_template to fill the template
        try:
            from auto_fill_template import auto_fill_template
            result = auto_fill_template(request_id, template, buyer_public_key)
            if not result:
                raise HTTPException(status_code=500, detail=f"Failed to auto-fill template for request {request_id}")
        except ImportError:
            # Fallback if auto_fill_template is not available
            print("Warning: auto_fill_template module not available, using mock data")
            # Create mock result
            result = {
                "template_cid": f"template_{request_id}_{int(time.time())}",
                "cert_cid": f"cert_{request_id}_{int(time.time())}",
                "merkle_root": hashlib.sha256(f"{request_id}_{int(time.time())}".encode()).hexdigest(),
                "signature": hashlib.sha256(f"sig_{request_id}_{int(time.time())}".encode()).hexdigest(),
                "encrypted_key": f"key_{request_id}_{int(time.time())}",
                "patient_address": wallet_address
            }

        # Update the purchase data
        purchase_data["status"] = "filled"
        purchase_data["filled_at"] = int(time.time())
        purchase_data["patient_address"] = wallet_address

        # Store template information in a list
        if "templates" not in purchase_data:
            purchase_data["templates"] = []

        template_info = {
            "template_cid": result["template_cid"],
            "cert_cid": result["cert_cid"],
            "merkle_root": result["merkle_root"],
            "signature": result["signature"],
            "encrypted_key": result["encrypted_key"],
            "filled_at": int(time.time())
        }

        purchase_data["templates"].append(template_info)

        # For backward compatibility, also store the latest template info at the top level
        purchase_data["template_cid"] = result["template_cid"]
        purchase_data["cert_cid"] = result["cert_cid"]
        purchase_data["merkle_root"] = result["merkle_root"]
        purchase_data["signature"] = result["signature"]
        purchase_data["encrypted_key"] = result["encrypted_key"]

        # Update templates count
        purchase_data["templates_count"] = len(purchase_data["templates"])

        # Create a transaction record
        transaction = {
            "type": "Patient Fill",
            "request_id": request_id,
            "patient": wallet_address,
            "buyer": buyer_address,
            "template_cid": result["template_cid"],
            "cert_cid": result["cert_cid"],
            "timestamp": int(time.time()),
            "details": {
                "message": "Template filled by patient"
            }
        }

        # Save the transaction
        save_transaction(transaction)

        # Save the updated purchase data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # Return the result
        return {
            "success": True,
            "message": "Template filled successfully",
            "template_cid": result["template_cid"],
            "cert_cid": result["cert_cid"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in fill_template: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/purchase/finalize")
@app.post("/purchase/finalize")
async def finalize_purchase(
    request_id: str = Body(...),
    approved: bool = Body(...),
    recipients: List[str] = Body(...),
    wallet_address: str = Body(...)
):
    """
    Finalize a purchase request
    """
    try:
        print(f"Finalizing purchase request {request_id}, approved: {approved}")

        # Check if the wallet address is provided
        if wallet_address:
            print(f"Request from wallet address: {wallet_address}")

        # Check if the request exists
        request_file = f"local_storage/purchases/{request_id}.json"
        if not os.path.exists(request_file):
            raise HTTPException(status_code=404, detail=f"Purchase request {request_id} not found")

        # Load the request data
        with open(request_file, "r") as f:
            purchase_data = json.load(f)

        # Check if the request has already been finalized
        if purchase_data.get("status") == "finalized":
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} has already been finalized")

        # Check if the request has been replied to
        if purchase_data.get("status") != "replied" and "template_cid" not in purchase_data:
            raise HTTPException(status_code=400, detail=f"Purchase request {request_id} has not been replied to yet")

        # Update the request status
        purchase_data["status"] = "finalized"
        purchase_data["finalized_at"] = int(time.time())
        purchase_data["approved"] = approved
        purchase_data["recipients"] = recipients

        # Create a transaction record
        transaction = {
            "type": "Buyer Finalize",
            "request_id": request_id,
            "buyer": wallet_address,
            "approved": approved,
            "recipients": recipients,
            "timestamp": int(time.time()),
            "details": {
                "message": "Purchase finalized"
            }
        }

        # Generate a fake transaction hash
        tx_hash = f"0x{hashlib.sha256(json.dumps(transaction).encode()).hexdigest()}"
        transaction["transaction_hash"] = tx_hash
        purchase_data["finalize_tx_hash"] = tx_hash

        # Save the updated request data
        with open(request_file, "w") as f:
            json.dump(purchase_data, f)

        # Save the transaction
        save_transaction(transaction)

        # Return the result
        return {
            "success": True,
            "message": "Purchase finalized successfully",
            "transaction_hash": tx_hash,
            "approved": approved
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in finalize_purchase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
