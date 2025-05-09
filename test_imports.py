#!/usr/bin/env python3
"""
Simple test script to check if the circular import issue is fixed.
"""

print("Importing constants...")
from backend.constants import ROLES, PATIENT_ADDRESS, DOCTOR_ADDRESS

print("Importing auth_utils...")
from backend.auth_utils import generate_auth_challenge, verify_auth_signature, is_authenticated, get_role

print("Importing api...")
import backend.api

print("All imports successful!")
