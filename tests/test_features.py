#!/usr/bin/env python3
"""
Comprehensive test script for the healthcare data sharing system.

This script tests the following features:
1. Authentication system
2. Hospital verification
3. Template processing
4. End-to-end workflow

Usage:
    python tests/test_features.py
"""

import os
import sys
import json
import time
import hashlib
import requests
import unittest
from web3 import Web3
from eth_account.messages import encode_defunct

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from backend.auth_utils import generate_auth_challenge, verify_auth_signature, is_authenticated
from backend.groupsig_utils import sign_message, verify_signature, open_signature_group_manager
from backend.auto_fill_template import auto_fill_template, get_patient_records, filter_records_by_template

# Test accounts
TEST_ACCOUNTS = {
    "Patient 1": {
        "address": "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",
        "private_key": "0x91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e",
        "role": "patient"
    },
    "Doctor 1": {
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "role": "doctor"
    },
    "Hospital 1": {
        "address": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",
        "private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "role": "hospital"
    },
    "Buyer 1": {
        "address": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",
        "private_key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "role": "buyer"
    },
    "Group Manager": {
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "private_key": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        "role": "group_manager"
    },
    "Revocation Manager": {
        "address": "0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46",
        "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        "role": "revocation_manager"
    }
}

# API endpoint
API_URL = os.getenv("API_URL", "http://localhost:8000/api")

class TestFeatures(unittest.TestCase):
    """Test class for healthcare data sharing features."""

    def setUp(self):
        """Set up test environment."""
        # Create local storage directories if they don't exist
        os.makedirs("local_storage", exist_ok=True)
        os.makedirs("local_storage/records", exist_ok=True)
        os.makedirs("local_storage/purchases", exist_ok=True)
        os.makedirs("local_storage/transactions", exist_ok=True)
        os.makedirs("secure_data", exist_ok=True)

        # Create a test record
        self.create_test_record()

    def create_test_record(self):
        """Create a test medical record for testing."""
        record = {
            "patientID": TEST_ACCOUNTS["Patient 1"]["address"],
            "doctorID": TEST_ACCOUNTS["Doctor 1"]["address"],
            "hospitalInfo": "General Hospital",
            "date": "2023-06-15",
            "category": "Cardiology",
            "demographics": {
                "age": 45,
                "gender": "Male",
                "location": "New York",
                "ethnicity": "Caucasian"
            },
            "medical_data": {
                "diagnosis": "Hypertension",
                "treatment": "Medication and lifestyle changes",
                "medications": "Lisinopril 10mg daily",
                "lab_results": "Blood pressure: 140/90 mmHg"
            },
            "notes": "Patient should follow up in 3 months."
        }

        # Save the record to local storage
        record_id = hashlib.sha256(json.dumps(record).encode()).hexdigest()
        with open(f"local_storage/records/{record_id}.json", "w") as f:
            json.dump(record, f)

        self.test_record = record
        self.test_record_id = record_id

    def test_1_authentication(self):
        """Test the authentication system."""
        print("\n=== Testing Authentication System ===")

        # Test generate_auth_challenge
        patient_address = TEST_ACCOUNTS["Patient 1"]["address"]
        challenge = generate_auth_challenge(patient_address)
        print(f"Generated challenge: {challenge}")
        self.assertIsNotNone(challenge)
        self.assertIn("Sign this message", challenge)

        # Test verify_auth_signature
        private_key = TEST_ACCOUNTS["Patient 1"]["private_key"]
        message_hash = encode_defunct(text=challenge)
        w3 = Web3()
        signed_message = w3.eth.account.sign_message(message_hash, private_key=private_key)
        signature = signed_message.signature.hex()

        result = verify_auth_signature(patient_address, signature)
        print(f"Signature verification result: {result}")
        self.assertTrue(result)

        # Test is_authenticated
        authenticated = is_authenticated(patient_address)
        print(f"Authentication status: {authenticated}")
        self.assertTrue(authenticated)

        print("Authentication system tests passed!")

    def test_2_hospital_verification(self):
        """Test the hospital verification process."""
        print("\n=== Testing Hospital Verification ===")

        # Test sign_message
        message = "test_message"
        signature = sign_message(message)
        print(f"Generated signature: {signature[:20]}...")
        self.assertIsNotNone(signature)

        # Test verify_signature
        verification_result = verify_signature(message, signature)
        print(f"Signature verification result: {verification_result}")
        self.assertTrue(verification_result)

        # Test open_signature_group_manager
        opening_result = open_signature_group_manager(signature)
        print(f"Signature opening result: {opening_result}")
        self.assertIsNotNone(opening_result)
        self.assertIn("status", opening_result)
        self.assertEqual(opening_result["status"], "success")

        print("Hospital verification tests passed!")

    def test_3_template_processing(self):
        """Test the template processing functionality."""
        print("\n=== Testing Template Processing ===")

        # Test get_patient_records
        patient_address = TEST_ACCOUNTS["Patient 1"]["address"]
        records = get_patient_records(patient_address)
        print(f"Found {len(records)} records for patient {patient_address}")
        self.assertGreater(len(records), 0)

        # Create a template
        template = {
            "category": "Cardiology",
            "demographics": {
                "age": True,
                "gender": True
            },
            "medical_data": {
                "diagnosis": True,
                "treatment": True
            },
            "min_records": 1,
            "max_records": 5
        }

        # Test filter_records_by_template
        filtered_records = filter_records_by_template(records, template)
        print(f"After filtering, {len(filtered_records)} records match the template")
        self.assertGreater(len(filtered_records), 0)

        # Test auto_fill_template
        request_id = f"test_request_{int(time.time())}"
        result = auto_fill_template(request_id, template)
        print(f"Template auto-fill result: {result}")
        self.assertIsNotNone(result)
        self.assertIn("template_cid", result)
        self.assertIn("cert_cid", result)
        self.assertIn("merkle_root", result)
        self.assertIn("signature", result)

        print("Template processing tests passed!")

    def test_4_end_to_end_workflow(self):
        """Test the end-to-end workflow."""
        print("\n=== Testing End-to-End Workflow ===")

        # 1. Doctor creates and signs a record
        doctor_address = TEST_ACCOUNTS["Doctor 1"]["address"]
        patient_address = TEST_ACCOUNTS["Patient 1"]["address"]

        record_data = {
            "patientID": patient_address,
            "doctorID": doctor_address,
            "hospitalInfo": "General Hospital",
            "date": "2023-06-15",
            "category": "Cardiology",
            "demographics": {
                "age": 45,
                "gender": "Male",
                "location": "New York",
                "ethnicity": "Caucasian"
            },
            "medical_data": {
                "diagnosis": "Hypertension",
                "treatment": "Medication and lifestyle changes",
                "medications": "Lisinopril 10mg daily",
                "lab_results": "Blood pressure: 140/90 mmHg"
            },
            "notes": "Patient should follow up in 3 months."
        }

        # Sign the record
        from backend.data import MerkleService
        merkle_service = MerkleService()
        merkle_root, proofs = merkle_service.create_merkle_tree(record_data)
        signature = sign_message(merkle_root)
        
        print(f"Record signed with merkle_root: {merkle_root[:20]}...")
        print(f"Signature: {signature[:20]}...")

        # 2. Buyer creates a purchase request
        buyer_address = TEST_ACCOUNTS["Buyer 1"]["address"]
        template = {
            "category": "Cardiology",
            "demographics": {
                "age": True,
                "gender": True
            },
            "medical_data": {
                "diagnosis": True,
                "treatment": True
            },
            "min_records": 1,
            "max_records": 5
        }

        request_id = f"test_request_{int(time.time())}"
        
        # 3. Hospital processes the request
        hospital_address = TEST_ACCOUNTS["Hospital 1"]["address"]
        
        # 4. Patient fills the template
        result = auto_fill_template(request_id, template)
        print(f"Template auto-fill result: {result}")
        self.assertIsNotNone(result)
        
        # 5. Buyer verifies the template
        verification_result = verify_signature(result["merkle_root"], result["signature"])
        print(f"Template verification result: {verification_result}")
        self.assertTrue(verification_result)

        print("End-to-end workflow tests passed!")

if __name__ == "__main__":
    unittest.main()
