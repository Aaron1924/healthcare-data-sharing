"""
Constants for the healthcare data sharing platform.

This module defines constants used throughout the application, including
default addresses for each role and role definitions.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Role definitions
ROLES = {
    "PATIENT": "patient",
    "DOCTOR": "doctor",
    "HOSPITAL": "hospital",
    "BUYER": "buyer",
    "GROUP_MANAGER": "group_manager",
    "REVOCATION_MANAGER": "revocation_manager"
}

# Default addresses for each role
PATIENT_ADDRESS = os.getenv("PATIENT_ADDRESS", "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A")
DOCTOR_ADDRESS = os.getenv("DOCTOR_ADDRESS", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
HOSPITAL_ADDRESS = os.getenv("HOSPITAL_ADDRESS", "0x28B317594b44483D24EE8AdCb13A1b148497C6ba")
BUYER_ADDRESS = os.getenv("BUYER_ADDRESS", "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce")
GROUP_MANAGER_ADDRESS = os.getenv("GROUP_MANAGER_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
REVOCATION_MANAGER_ADDRESS = os.getenv("REVOCATION_MANAGER_ADDRESS", "0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46")

# Default wallet address (for backward compatibility)
WALLET_ADDRESS = PATIENT_ADDRESS

# Contract address
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA")

# RPC URL
BASE_SEPOLIA_RPC_URL = os.getenv("BASE_SEPOLIA_RPC_URL", "https://api.developer.coinbase.com/rpc/v1/base-sepolia/TU79b5nxSoHEPVmNhElKsyBqt9CUbNTf")

# IPFS URL
IPFS_URL = os.getenv("IPFS_URL", "/ip4/127.0.0.1/tcp/5001")

# Default private key
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e")
