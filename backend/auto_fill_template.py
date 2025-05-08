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
from typing import Dict, List, Any, Optional

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
            "record_id": record.get("cid", hashlib.sha256(json.dumps(record).encode()).hexdigest()),
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
    """Upload data to IPFS and return the CID."""
    try:
        # Try to connect to IPFS
        ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')

        # Convert data to JSON string
        json_data = json.dumps(data)

        # Add to IPFS
        result = ipfs_client.add_json(json_data)

        # Return the CID
        return result
    except Exception as e:
        print(f"Error uploading to IPFS: {str(e)}")

        # Fallback to local storage
        cid = hashlib.sha256(json.dumps(data).encode()).hexdigest()

        # Save to local storage
        os.makedirs("local_storage", exist_ok=True)
        with open(f"local_storage/{cid}", "w") as f:
            json.dump(data, f)

        return cid

def auto_fill_template(request_id: str, template: Dict[str, Any], buyer_public_key: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    """
    Automatically fill a template for Patient 1 following the secure workflow.

    Args:
        request_id: The purchase request ID
        template: The template to fill
        buyer_public_key: The buyer's public key for encrypting the temporary key

    Returns:
        A dictionary containing the CID and other metadata, or None if an error occurred
    """
    try:
        print(f"Auto-filling template for request {request_id}")

        # Get Patient 1's records
        records = get_patient_records(PATIENT_1_ADDRESS)
        print(f"Found {len(records)} records for Patient 1")

        # Filter records based on template
        filtered_records = filter_records_by_template(records, template)
        print(f"After filtering, {len(filtered_records)} records match the template")

        # Check if we have enough records
        min_records = template.get("min_records", 1)
        if len(filtered_records) < min_records:
            print(f"Not enough records: found {len(filtered_records)}, need {min_records}")
            return None

        # For demo purposes, just use the first matching record
        selected_record = filtered_records[0]
        print(f"Selected record: {selected_record.get('cid', 'No CID')}")

        # Create a filled template with just the selected record
        filled_template = {
            "template": template,
            "record": selected_record,
            "patient_address": PATIENT_1_ADDRESS,
            "timestamp": int(time.time()),
            "request_id": request_id
        }

        # Create Merkle tree from the record data
        try:
            # Import MerkleService from backend.data
            from backend.data import MerkleService
            merkle_service = MerkleService()
            merkle_root, proofs = merkle_service.create_merkle_tree(selected_record)
            filled_template["merkle_root"] = merkle_root
            filled_template["merkle_proofs"] = proofs
            print(f"Created Merkle tree with root: {merkle_root}")
        except ImportError:
            # Fallback if MerkleService is not available
            print("Warning: MerkleService not available, using hash as Merkle root")
            merkle_root = hashlib.sha256(json.dumps(selected_record).encode()).hexdigest()
            filled_template["merkle_root"] = merkle_root
            filled_template["merkle_proofs"] = {}

        # Sign the Merkle root with group signature
        try:
            # Import sign_message from backend.groupsig_utils
            from backend.groupsig_utils import sign_message
            signature = sign_message(merkle_root)
            if signature:
                filled_template["signature"] = signature
                print(f"Signed Merkle root with group signature: {signature[:20]}...")
            else:
                # Fallback if signing fails
                print("Warning: Group signature failed, using mock signature")
                signature = hashlib.sha256(f"{merkle_root}_{int(time.time())}".encode()).hexdigest()
                filled_template["signature"] = signature
        except ImportError:
            # Fallback if sign_message is not available
            print("Warning: sign_message not available, using mock signature")
            signature = hashlib.sha256(f"{merkle_root}_{int(time.time())}".encode()).hexdigest()
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
            # Simple encryption for demo purposes
            nonce = os.urandom(16)
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            cipher = Cipher(algorithms.AES(temp_key), modes.CTR(nonce), backend=default_backend())
            encryptor = cipher.encryptor()
            template_json = json.dumps(filled_template).encode()
            ciphertext = encryptor.update(template_json) + encryptor.finalize()
            encrypted_template = nonce + ciphertext

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
            "merkle_root": merkle_root,
            "signature": signature,
            "encrypted_key": encrypted_temp_key
        }

        # Upload the CERT to IPFS
        cert_cid = upload_to_ipfs(json.dumps(cert).encode())
        print(f"Uploaded CERT to IPFS with CID: {cert_cid}")

        # Return the result
        return {
            "template_cid": template_cid,
            "cert_cid": cert_cid,
            "merkle_root": merkle_root,
            "signature": signature,
            "encrypted_key": encrypted_temp_key,
            "patient_address": PATIENT_1_ADDRESS
        }
    except Exception as e:
        print(f"Error auto-filling template: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
