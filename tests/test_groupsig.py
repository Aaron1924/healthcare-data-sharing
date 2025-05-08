#!/usr/bin/env python3
"""
Group signature test script for the healthcare data sharing system.

This script tests the group signature functionality:
1. Signing messages
2. Verifying signatures
3. Opening signatures (group manager)
4. Opening signatures (revocation manager)
5. Full signature opening

Usage:
    python tests/test_groupsig.py
"""

import os
import sys
import json
import time
import hashlib
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from backend.groupsig_utils import (
    sign_message, 
    verify_signature, 
    open_signature_group_manager, 
    open_signature_revocation_manager, 
    open_signature_full,
    get_doctor_info
)

class TestGroupSig(unittest.TestCase):
    """Test class for group signature functionality."""

    def test_1_sign_message(self):
        """Test signing messages with group signatures."""
        print("\n=== Testing Message Signing ===")
        
        # Test with different message types
        test_messages = [
            "Simple text message",
            "Message with special characters: !@#$%^&*()",
            "1234567890",
            json.dumps({"key": "value", "nested": {"key": "value"}}),
            hashlib.sha256(b"Binary data").hexdigest()
        ]
        
        for i, message in enumerate(test_messages):
            signature = sign_message(message)
            print(f"Message {i+1}: {message[:30]}...")
            print(f"Signature {i+1}: {signature[:30]}...")
            self.assertIsNotNone(signature)
            
        print("Message signing tests passed!")

    def test_2_verify_signature(self):
        """Test verifying group signatures."""
        print("\n=== Testing Signature Verification ===")
        
        # Test with different message types
        test_messages = [
            "Simple text message",
            "Message with special characters: !@#$%^&*()",
            "1234567890",
            json.dumps({"key": "value", "nested": {"key": "value"}}),
            hashlib.sha256(b"Binary data").hexdigest()
        ]
        
        for i, message in enumerate(test_messages):
            signature = sign_message(message)
            verification_result = verify_signature(message, signature)
            print(f"Message {i+1}: {message[:30]}...")
            print(f"Verification result {i+1}: {verification_result}")
            self.assertTrue(verification_result)
            
        # Test with invalid signature
        invalid_signature = "invalid_signature"
        verification_result = verify_signature(test_messages[0], invalid_signature)
        print(f"Invalid signature verification result: {verification_result}")
        self.assertFalse(verification_result)
        
        # Test with modified message
        message = "Original message"
        signature = sign_message(message)
        modified_message = "Modified message"
        verification_result = verify_signature(modified_message, signature)
        print(f"Modified message verification result: {verification_result}")
        self.assertFalse(verification_result)
        
        print("Signature verification tests passed!")

    def test_3_open_signature_group_manager(self):
        """Test opening signatures as the group manager."""
        print("\n=== Testing Group Manager Signature Opening ===")
        
        # Sign a message
        message = "Test message for group manager opening"
        signature = sign_message(message)
        print(f"Message: {message}")
        print(f"Signature: {signature[:30]}...")
        
        # Open the signature as the group manager
        opening_result = open_signature_group_manager(signature)
        print(f"Opening result: {opening_result}")
        self.assertIsNotNone(opening_result)
        self.assertIn("status", opening_result)
        self.assertEqual(opening_result["status"], "success")
        
        # Save the partial opening result for the next test
        self.partial_g = opening_result.get("partial_g")
        
        print("Group manager signature opening tests passed!")

    def test_4_open_signature_revocation_manager(self):
        """Test opening signatures as the revocation manager."""
        print("\n=== Testing Revocation Manager Signature Opening ===")
        
        # Sign a message
        message = "Test message for revocation manager opening"
        signature = sign_message(message)
        print(f"Message: {message}")
        print(f"Signature: {signature[:30]}...")
        
        # Get the group manager's partial opening
        gm_opening_result = open_signature_group_manager(signature)
        partial_g = gm_opening_result.get("partial_g")
        
        # Open the signature as the revocation manager
        opening_result = open_signature_revocation_manager(signature, partial_g)
        print(f"Opening result: {opening_result}")
        self.assertIsNotNone(opening_result)
        self.assertIn("status", opening_result)
        self.assertEqual(opening_result["status"], "success")
        
        # Save the partial opening result for the next test
        self.partial_r = opening_result.get("partial_r")
        
        print("Revocation manager signature opening tests passed!")

    def test_5_open_signature_full(self):
        """Test full signature opening."""
        print("\n=== Testing Full Signature Opening ===")
        
        # Sign a message
        message = "Test message for full opening"
        signature = sign_message(message)
        print(f"Message: {message}")
        print(f"Signature: {signature[:30]}...")
        
        # Get the group manager's partial opening
        gm_opening_result = open_signature_group_manager(signature)
        partial_g = gm_opening_result.get("partial_g")
        
        # Get the revocation manager's partial opening
        rm_opening_result = open_signature_revocation_manager(signature, partial_g)
        partial_r = rm_opening_result.get("partial_r")
        
        # Perform full opening
        opening_result = open_signature_full(signature, partial_g, partial_r)
        print(f"Opening result: {opening_result}")
        self.assertIsNotNone(opening_result)
        self.assertIn("status", opening_result)
        self.assertEqual(opening_result["status"], "success")
        self.assertIn("signer", opening_result)
        self.assertIn("signer_details", opening_result)
        
        # Check signer details
        signer_details = opening_result["signer_details"]
        print(f"Signer details: {signer_details}")
        self.assertIn("name", signer_details)
        self.assertIn("specialty", signer_details)
        self.assertIn("hospital", signer_details)
        self.assertIn("license", signer_details)
        
        print("Full signature opening tests passed!")

    def test_6_get_doctor_info(self):
        """Test getting doctor information."""
        print("\n=== Testing Doctor Info Retrieval ===")
        
        # Test with different doctor IDs
        test_ids = [
            "doctor_123",
            "doctor_456",
            "doctor_789",
            "12345"
        ]
        
        for i, doctor_id in enumerate(test_ids):
            doctor_info = get_doctor_info(doctor_id)
            print(f"Doctor ID {i+1}: {doctor_id}")
            print(f"Doctor info {i+1}: {doctor_info}")
            self.assertIsNotNone(doctor_info)
            self.assertIn("name", doctor_info)
            self.assertIn("specialty", doctor_info)
            self.assertIn("hospital", doctor_info)
            self.assertIn("license", doctor_info)
            self.assertIn("years_experience", doctor_info)
            
        print("Doctor info retrieval tests passed!")

if __name__ == "__main__":
    unittest.main()
