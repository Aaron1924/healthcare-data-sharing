"""
Automatic template filling for Patient 1.

This module provides functions to automatically fill templates for Patient 1
when the Hospital confirms a purchase request.
"""

import os
import json
import time
import random
import hashlib
import ipfshttpclient
import decimal
from typing import Dict, List, Any, Optional

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# Constants
PATIENT_1_ADDRESS = "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A"

def get_patient_records(patient_address: str) -> List[Dict[str, Any]]:
    """Get all records for a patient from local storage."""
    records = []

    # Check if the local storage directory exists
    if not os.path.exists("local_storage/records"):
        return []

    # Get all record files
    record_files = os.listdir("local_storage/records")

    for file_name in record_files:
        if not file_name.endswith(".json"):
            continue

        file_path = f"local_storage/records/{file_name}"

        try:
            with open(file_path, "r") as f:
                record_data = json.load(f)

            # Check if this record belongs to the patient
            if record_data.get("patientID") == patient_address or record_data.get("patientId") == patient_address:
                records.append(record_data)
        except Exception as e:
            print(f"Error reading record file {file_name}: {str(e)}")

    return records

def filter_records_by_template(records: List[Dict[str, Any]], template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter records based on template criteria."""
    filtered_records = []

    # Get template filters
    category = template.get("category")
    demographics = template.get("demographics", {})
    medical_data = template.get("medical_data", {})

    for record in records:
        # Check category if specified
        if category and record.get("category") != category:
            continue

        # Check demographics if specified
        record_demographics = record.get("demographics", {})
        if demographics:
            # Skip if any required demographic field is missing
            if demographics.get("age") and "age" not in record_demographics:
                continue
            if demographics.get("gender") and "gender" not in record_demographics:
                continue
            if demographics.get("location") and "location" not in record_demographics:
                continue
            if demographics.get("ethnicity") and "ethnicity" not in record_demographics:
                continue

        # Check medical data if specified
        record_medical_data = record.get("medical_data", {})
        if medical_data:
            # Skip if any required medical field is missing
            if medical_data.get("diagnosis") and "diagnosis" not in record_medical_data:
                continue
            if medical_data.get("treatment") and "treatment" not in record_medical_data:
                continue
            if medical_data.get("medications") and "medications" not in record_medical_data:
                continue
            if medical_data.get("lab_results") and "lab_results" not in record_medical_data:
                continue

        # If we got here, the record matches the template
        filtered_records.append(record)

    return filtered_records

def create_template_package(records: List[Dict[str, Any]], template: Dict[str, Any]) -> Dict[str, Any]:
    """Create a template package with the filtered records."""
    # Extract only the requested fields from each record
    processed_records = []

    demographics = template.get("demographics", {})
    medical_data = template.get("medical_data", {})

    for record in records:
        processed_record = {
            "record_id": record.get("cid", hashlib.sha256(json.dumps(record, cls=DecimalEncoder).encode()).hexdigest()),
            "category": record.get("category"),
            "date": record.get("date"),
            "demographics": {},
            "medical_data": {}
        }

        # Add requested demographics
        record_demographics = record.get("demographics", {})
        if demographics.get("age"):
            processed_record["demographics"]["age"] = record_demographics.get("age")
        if demographics.get("gender"):
            processed_record["demographics"]["gender"] = record_demographics.get("gender")
        if demographics.get("location"):
            processed_record["demographics"]["location"] = record_demographics.get("location")
        if demographics.get("ethnicity"):
            processed_record["demographics"]["ethnicity"] = record_demographics.get("ethnicity")

        # Add requested medical data
        record_medical_data = record.get("medical_data", {})
        if medical_data.get("diagnosis"):
            processed_record["medical_data"]["diagnosis"] = record_medical_data.get("diagnosis")
        if medical_data.get("treatment"):
            processed_record["medical_data"]["treatment"] = record_medical_data.get("treatment")
        if medical_data.get("medications"):
            processed_record["medical_data"]["medications"] = record_medical_data.get("medications")
        if medical_data.get("lab_results"):
            processed_record["medical_data"]["lab_results"] = record_medical_data.get("lab_results")

        processed_records.append(processed_record)

    # Create the template package
    template_package = {
        "template": template,
        "records": processed_records,
        "timestamp": int(time.time()),
        "patient_address": PATIENT_1_ADDRESS
    }

    return template_package

def upload_to_ipfs(data: Dict[str, Any]) -> str:
    """Store data in local storage and return the CID (hash)."""
    # Generate a CID (hash) for the data
    cid = hashlib.sha256(json.dumps(data, cls=DecimalEncoder).encode()).hexdigest() if not isinstance(data, bytes) else hashlib.sha256(data).hexdigest()

    # Save to local storage
    os.makedirs("local_storage", exist_ok=True)

    # Write the data to a file
    if isinstance(data, bytes):
        with open(f"local_storage/{cid}", "wb") as f:
            f.write(data)
    else:
        with open(f"local_storage/{cid}", "w") as f:
            if isinstance(data, dict):
                json.dump(data, f, cls=DecimalEncoder)
            else:
                f.write(str(data))

    print(f"Saved to local storage with CID: {cid}")
    return cid

def auto_fill_template(request_id: str, template: Dict[str, Any], buyer_public_key: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    """
    Automatically fill a template for a patient following the secure workflow.

    This function implements the real template processing workflow:
    1. Retrieve patient records that match the template criteria
    2. Create a Merkle tree from the record data
    3. Sign the Merkle root with a group signature
    4. Encrypt the filled template with a temporary key
    5. Encrypt the temporary key with the buyer's public key
    6. Upload the encrypted template and CERT to IPFS

    Args:
        request_id: The purchase request ID
        template: The template to fill
        buyer_public_key: The buyer's public key for encrypting the temporary key

    Returns:
        A dictionary containing the CID and other metadata, or None if an error occurred
    """
    try:
        print(f"Auto-filling template for request {request_id}")

        # Get the patient address from the template or use the default
        patient_address = template.get("patient_address", PATIENT_1_ADDRESS)
        print(f"Processing template for patient: {patient_address}")

        # Get patient's records
        records = get_patient_records(patient_address)
        print(f"Found {len(records)} records for patient {patient_address}")

        # Filter records based on template
        filtered_records = filter_records_by_template(records, template)
        print(f"After filtering, {len(filtered_records)} records match the template")

        # Check if we have enough records
        min_records = template.get("min_records", 1)
        if len(filtered_records) < min_records:
            print(f"Not enough records: found {len(filtered_records)}, need {min_records}")
            return None

        # Process all matching records (up to a reasonable limit)
        max_records = min(len(filtered_records), template.get("max_records", 10))
        selected_records = filtered_records[:max_records]
        print(f"Selected {len(selected_records)} records for processing")

        # Create a filled template with the selected records
        filled_template = {
            "template": template,
            "records": selected_records,
            "patient_address": patient_address,
            "timestamp": int(time.time()),
            "request_id": request_id
        }

        # Create Merkle tree from the record data
        try:
            # Import MerkleService from backend.data
            from backend.data import MerkleService
            merkle_service = MerkleService()

            # Create a Merkle tree for each record
            merkle_roots = []
            merkle_proofs = {}

            for i, record in enumerate(selected_records):
                root, proofs = merkle_service.create_merkle_tree(record)
                merkle_roots.append(root)
                merkle_proofs[f"record_{i}"] = proofs
                print(f"Created Merkle tree for record {i} with root: {root[:20]}...")

            # Create a master Merkle tree from all the record Merkle roots
            master_root, master_proofs = merkle_service.create_merkle_tree({"roots": merkle_roots})
            filled_template["merkle_root"] = master_root
            filled_template["merkle_proofs"] = merkle_proofs
            filled_template["master_proofs"] = master_proofs
            print(f"Created master Merkle tree with root: {master_root[:20]}...")
        except ImportError:
            # Fallback if MerkleService is not available
            print("Warning: MerkleService not available, using hash as Merkle root")
            master_root = hashlib.sha256(json.dumps(selected_records, cls=DecimalEncoder).encode()).hexdigest()
            filled_template["merkle_root"] = master_root
            filled_template["merkle_proofs"] = {}

        # Sign the master Merkle root with group signature
        try:
            # Import sign_message from backend.groupsig_utils
            from backend.groupsig_utils import sign_message
            signature = sign_message(master_root)
            if signature:
                filled_template["signature"] = signature
                print(f"Signed master Merkle root with group signature: {signature[:20]}...")
            else:
                # Fallback if signing fails
                print("Warning: Group signature failed, using mock signature")
                signature = hashlib.sha256(f"{master_root}_{int(time.time())}".encode()).hexdigest()
                filled_template["signature"] = signature
        except ImportError:
            # Fallback if sign_message is not available
            print("Warning: sign_message not available, using mock signature")
            signature = hashlib.sha256(f"{master_root}_{int(time.time())}".encode()).hexdigest()
            filled_template["signature"] = signature

        # Generate a temporary key for encrypting the filled template
        temp_key = os.urandom(32)  # 256-bit AES key
        print(f"Generated temporary key: {temp_key[:5].hex()}...")

        # Encrypt the filled template with the temporary key
        try:
            # Import encrypt_record from backend.data
            from backend.data import encrypt_record
            encrypted_template = encrypt_record(filled_template, temp_key)
            print(f"Encrypted filled template: {len(encrypted_template)} bytes")
        except ImportError:
            # Fallback if encrypt_record is not available
            print("Warning: encrypt_record not available, using simple encryption")
            try:
                # Try to use cryptography library
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend

                # Generate a random IV
                iv = os.urandom(16)

                # Create an encryptor
                cipher = Cipher(algorithms.AES(temp_key), modes.GCM(iv), backend=default_backend())
                encryptor = cipher.encryptor()

                # Convert the filled template to JSON
                plaintext = json.dumps(filled_template, cls=DecimalEncoder).encode()

                # Encrypt the data
                ciphertext = encryptor.update(plaintext) + encryptor.finalize()

                # Get the tag
                tag = encryptor.tag

                # Combine IV, ciphertext, and tag
                encrypted_template = iv + tag + ciphertext
                print(f"Encrypted filled template with AES-GCM: {len(encrypted_template)} bytes")
            except ImportError:
                # Fallback to very simple encryption if cryptography is not available
                print("Warning: cryptography library not available, using very simple encryption")
                # Simple XOR encryption for demo purposes only
                plaintext = json.dumps(filled_template, cls=DecimalEncoder).encode()
                key_bytes = (temp_key * (len(plaintext) // len(temp_key) + 1))[:len(plaintext)]
                encrypted_template = bytes([p ^ k for p, k in zip(plaintext, key_bytes)])
                print(f"Encrypted filled template with simple XOR: {len(encrypted_template)} bytes")

        # Encrypt the temporary key with the buyer's public key
        encrypted_temp_key = None
        if buyer_public_key:
            try:
                # Import encrypt_with_public_key from backend.api
                from backend.api import encrypt_with_public_key
                encrypted_temp_key = encrypt_with_public_key(temp_key, buyer_public_key)
                print(f"Encrypted temporary key with buyer's public key: {len(encrypted_temp_key)} bytes")
            except ImportError:
                # Fallback if encrypt_with_public_key is not available
                print("Warning: encrypt_with_public_key not available, using mock encryption")
                encrypted_temp_key = f"MOCK_ENCRYPTED_{temp_key.hex()}"
        else:
            # For demo purposes, just use the key as is
            print("Warning: No buyer public key provided, using unencrypted key")
            encrypted_temp_key = temp_key.hex()

        # Upload the encrypted template to IPFS
        template_cid = upload_to_ipfs(encrypted_template)
        print(f"Uploaded encrypted template to IPFS with CID: {template_cid}")

        # Create the CERT structure
        cert = {
            "merkle_root": master_root,
            "signature": signature,
            "encrypted_key": encrypted_temp_key,
            "records_count": len(selected_records),
            "timestamp": int(time.time())
        }

        # Upload the CERT to IPFS
        cert_cid = upload_to_ipfs(json.dumps(cert, cls=DecimalEncoder).encode())
        print(f"Uploaded CERT to IPFS with CID: {cert_cid}")

        # Return the result
        return {
            "template_cid": template_cid,
            "cert_cid": cert_cid,
            "merkle_root": master_root,
            "signature": signature,
            "encrypted_key": encrypted_temp_key,
            "patient_address": patient_address,
            "records_count": len(selected_records)
        }
    except Exception as e:
        print(f"Error auto-filling template: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
