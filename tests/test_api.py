#!/usr/bin/env python3
"""
API test script for the healthcare data sharing system.

This script tests the API endpoints for:
1. Authentication
2. Record creation and retrieval
3. Template processing
4. Purchase workflow

Usage:
    python tests/test_api.py
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

class TestAPI(unittest.TestCase):
    """Test class for healthcare data sharing API."""

    def setUp(self):
        """Set up test environment."""
        # Create local storage directories if they don't exist
        os.makedirs("local_storage", exist_ok=True)
        os.makedirs("local_storage/records", exist_ok=True)
        os.makedirs("local_storage/purchases", exist_ok=True)
        os.makedirs("local_storage/transactions", exist_ok=True)
        os.makedirs("secure_data", exist_ok=True)

        # Authenticate all accounts
        self.tokens = {}
        for account_name, account_info in TEST_ACCOUNTS.items():
            self.authenticate_account(account_name, account_info)

    def authenticate_account(self, account_name, account_info):
        """Authenticate an account with the API."""
        try:
            # Get a challenge
            response = requests.post(
                f"{API_URL}/auth/challenge",
                json={"wallet_address": account_info["address"]}
            )
            
            if response.status_code == 404:
                # Try alternative URL
                response = requests.post(
                    f"{API_URL}/api/auth/challenge",
                    json={"wallet_address": account_info["address"]}
                )
                
            if response.status_code != 200:
                print(f"Failed to get challenge for {account_name}: {response.text}")
                return
                
            challenge_data = response.json()
            challenge = challenge_data.get("challenge")
            
            # Sign the challenge
            message_hash = encode_defunct(text=challenge)
            w3 = Web3()
            signed_message = w3.eth.account.sign_message(
                message_hash,
                private_key=account_info["private_key"]
            )
            signature = signed_message.signature.hex()
            
            # Verify the signature
            verify_response = requests.post(
                f"{API_URL}/auth/verify",
                json={
                    "wallet_address": account_info["address"],
                    "signature": signature
                }
            )
            
            if verify_response.status_code == 404:
                # Try alternative URL
                verify_response = requests.post(
                    f"{API_URL}/api/auth/verify",
                    json={
                        "wallet_address": account_info["address"],
                        "signature": signature
                    }
                )
                
            if verify_response.status_code != 200:
                print(f"Failed to verify signature for {account_name}: {verify_response.text}")
                return
                
            auth_data = verify_response.json()
            if auth_data.get("authenticated", False):
                print(f"Authenticated {account_name} as {auth_data.get('role')}")
                self.tokens[account_name] = auth_data
            else:
                print(f"Authentication failed for {account_name}: {auth_data.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error authenticating {account_name}: {str(e)}")

    def test_1_health_check(self):
        """Test the health check endpoint."""
        print("\n=== Testing Health Check ===")
        
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 404:
            # Try alternative URL
            response = requests.get(f"{API_URL}/api/health")
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        print("Health check passed!")

    def test_2_create_record(self):
        """Test creating a medical record."""
        print("\n=== Testing Record Creation ===")
        
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
        
        response = requests.post(
            f"{API_URL}/records",
            json={
                "record": record_data,
                "wallet_address": doctor_address
            }
        )
        
        if response.status_code == 404:
            # Try alternative URL
            response = requests.post(
                f"{API_URL}/api/records",
                json={
                    "record": record_data,
                    "wallet_address": doctor_address
                }
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("cid", data)
        self.assertIn("merkle_root", data)
        self.assertIn("signature", data)
        
        # Save the record ID for later tests
        self.record_cid = data["cid"]
        self.merkle_root = data["merkle_root"]
        self.signature = data["signature"]
        
        print(f"Record created with CID: {self.record_cid}")
        print("Record creation test passed!")

    def test_3_get_patient_records(self):
        """Test retrieving patient records."""
        print("\n=== Testing Patient Records Retrieval ===")
        
        patient_address = TEST_ACCOUNTS["Patient 1"]["address"]
        
        response = requests.get(
            f"{API_URL}/patient/records",
            params={"wallet_address": patient_address}
        )
        
        if response.status_code == 404:
            # Try alternative URL
            response = requests.get(
                f"{API_URL}/api/patient/records",
                params={"wallet_address": patient_address}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("records", data)
        self.assertGreater(len(data["records"]), 0)
        
        print(f"Retrieved {len(data['records'])} records for patient {patient_address}")
        print("Patient records retrieval test passed!")

    def test_4_create_purchase_request(self):
        """Test creating a purchase request."""
        print("\n=== Testing Purchase Request Creation ===")
        
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
        
        response = requests.post(
            f"{API_URL}/purchases/request",
            json={
                "template": template,
                "wallet_address": buyer_address
            }
        )
        
        if response.status_code == 404:
            # Try alternative URL
            response = requests.post(
                f"{API_URL}/api/purchases/request",
                json={
                    "template": template,
                    "wallet_address": buyer_address
                }
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("request_id", data)
        
        # Save the request ID for later tests
        self.request_id = data["request_id"]
        
        print(f"Purchase request created with ID: {self.request_id}")
        print("Purchase request creation test passed!")

    def test_5_hospital_reply(self):
        """Test hospital replying to a purchase request."""
        print("\n=== Testing Hospital Reply ===")
        
        hospital_address = TEST_ACCOUNTS["Hospital 1"]["address"]
        
        response = requests.post(
            f"{API_URL}/purchases/reply",
            json={
                "request_id": self.request_id,
                "wallet_address": hospital_address
            }
        )
        
        if response.status_code == 404:
            # Try alternative URL
            response = requests.post(
                f"{API_URL}/api/purchases/reply",
                json={
                    "request_id": self.request_id,
                    "wallet_address": hospital_address
                }
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("template_cid", data)
        
        # Save the template CID for later tests
        self.template_cid = data["template_cid"]
        
        print(f"Hospital replied with template CID: {self.template_cid}")
        print("Hospital reply test passed!")

    def test_6_buyer_finalize(self):
        """Test buyer finalizing a purchase request."""
        print("\n=== Testing Buyer Finalization ===")
        
        buyer_address = TEST_ACCOUNTS["Buyer 1"]["address"]
        
        response = requests.post(
            f"{API_URL}/purchases/finalize",
            json={
                "request_id": self.request_id,
                "wallet_address": buyer_address,
                "approved": True
            }
        )
        
        if response.status_code == 404:
            # Try alternative URL
            response = requests.post(
                f"{API_URL}/api/purchases/finalize",
                json={
                    "request_id": self.request_id,
                    "wallet_address": buyer_address,
                    "approved": True
                }
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        
        print("Buyer finalization test passed!")

if __name__ == "__main__":
    unittest.main()
