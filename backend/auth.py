"""
Authentication system for the healthcare data sharing platform.

This module provides functions for authenticating users based on their wallet addresses
and managing role-based access control.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from web3 import Web3
from eth_account.messages import encode_defunct
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Role definitions
ROLES = {
    "PATIENT": "patient",
    "DOCTOR": "doctor",
    "HOSPITAL": "hospital",
    "BUYER": "buyer",
    "GROUP_MANAGER": "group_manager",
    "REVOCATION_MANAGER": "revocation_manager"
}

# In-memory storage for authenticated sessions
# Format: {wallet_address: {"role": role, "timestamp": timestamp, "nonce": nonce}}
authenticated_sessions = {}

# In-memory storage for role assignments
# Format: {wallet_address: role}
role_assignments = {}

# In-memory storage for authentication challenges
# Format: {wallet_address: {"nonce": nonce, "timestamp": timestamp}}
auth_challenges = {}

# Session expiration time (in seconds)
SESSION_EXPIRATION = 3600  # 1 hour

def load_role_assignments():
    """Load role assignments from a file."""
    try:
        if os.path.exists("secure_data/role_assignments.json"):
            with open("secure_data/role_assignments.json", "r") as f:
                global role_assignments
                role_assignments = json.load(f)
                logger.info(f"Loaded {len(role_assignments)} role assignments")
        else:
            logger.warning("Role assignments file not found, starting with empty assignments")
    except Exception as e:
        logger.error(f"Error loading role assignments: {str(e)}")

def save_role_assignments():
    """Save role assignments to a file."""
    try:
        os.makedirs("secure_data", exist_ok=True)
        with open("secure_data/role_assignments.json", "w") as f:
            json.dump(role_assignments, f)
            logger.info(f"Saved {len(role_assignments)} role assignments")
    except Exception as e:
        logger.error(f"Error saving role assignments: {str(e)}")

def assign_role(wallet_address: str, role: str) -> bool:
    """
    Assign a role to a wallet address.
    
    Args:
        wallet_address: The wallet address to assign the role to
        role: The role to assign
        
    Returns:
        bool: True if the role was assigned successfully, False otherwise
    """
    if role not in ROLES.values():
        logger.error(f"Invalid role: {role}")
        return False
    
    role_assignments[wallet_address.lower()] = role
    save_role_assignments()
    logger.info(f"Assigned role {role} to {wallet_address}")
    return True

def get_role(wallet_address: str) -> Optional[str]:
    """
    Get the role assigned to a wallet address.
    
    Args:
        wallet_address: The wallet address to get the role for
        
    Returns:
        str: The role assigned to the wallet address, or None if no role is assigned
    """
    return role_assignments.get(wallet_address.lower())

def generate_auth_challenge(wallet_address: str) -> str:
    """
    Generate an authentication challenge for a wallet address.
    
    Args:
        wallet_address: The wallet address to generate a challenge for
        
    Returns:
        str: The authentication challenge message
    """
    nonce = hashlib.sha256(os.urandom(32)).hexdigest()
    timestamp = int(time.time())
    
    auth_challenges[wallet_address.lower()] = {
        "nonce": nonce,
        "timestamp": timestamp
    }
    
    challenge_message = f"Sign this message to authenticate with the Healthcare Data Sharing platform: {nonce}"
    return challenge_message

def verify_auth_signature(wallet_address: str, signature: str) -> bool:
    """
    Verify an authentication signature.
    
    Args:
        wallet_address: The wallet address that signed the message
        signature: The signature to verify
        
    Returns:
        bool: True if the signature is valid, False otherwise
    """
    wallet_address = wallet_address.lower()
    
    if wallet_address not in auth_challenges:
        logger.error(f"No authentication challenge found for {wallet_address}")
        return False
    
    challenge = auth_challenges[wallet_address]
    nonce = challenge["nonce"]
    timestamp = challenge["timestamp"]
    
    # Check if the challenge has expired (5 minutes)
    if int(time.time()) - timestamp > 300:
        logger.error(f"Authentication challenge for {wallet_address} has expired")
        del auth_challenges[wallet_address]
        return False
    
    # Verify the signature
    try:
        message = f"Sign this message to authenticate with the Healthcare Data Sharing platform: {nonce}"
        message_hash = encode_defunct(text=message)
        
        # Recover the address from the signature
        w3 = Web3()
        recovered_address = w3.eth.account.recover_message(message_hash, signature=signature)
        
        # Check if the recovered address matches the claimed address
        if recovered_address.lower() != wallet_address:
            logger.error(f"Signature verification failed for {wallet_address}")
            return False
        
        # Create a session
        role = get_role(wallet_address)
        if not role:
            logger.warning(f"No role assigned to {wallet_address}")
            return False
        
        authenticated_sessions[wallet_address] = {
            "role": role,
            "timestamp": int(time.time()),
            "nonce": nonce
        }
        
        # Clean up the challenge
        del auth_challenges[wallet_address]
        
        logger.info(f"Authentication successful for {wallet_address} with role {role}")
        return True
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False

def is_authenticated(wallet_address: str) -> bool:
    """
    Check if a wallet address is authenticated.
    
    Args:
        wallet_address: The wallet address to check
        
    Returns:
        bool: True if the wallet address is authenticated, False otherwise
    """
    wallet_address = wallet_address.lower()
    
    if wallet_address not in authenticated_sessions:
        return False
    
    session = authenticated_sessions[wallet_address]
    timestamp = session["timestamp"]
    
    # Check if the session has expired
    if int(time.time()) - timestamp > SESSION_EXPIRATION:
        del authenticated_sessions[wallet_address]
        return False
    
    return True

def has_role(wallet_address: str, role: str) -> bool:
    """
    Check if a wallet address has a specific role.
    
    Args:
        wallet_address: The wallet address to check
        role: The role to check for
        
    Returns:
        bool: True if the wallet address has the specified role, False otherwise
    """
    wallet_address = wallet_address.lower()
    
    if not is_authenticated(wallet_address):
        return False
    
    session = authenticated_sessions[wallet_address]
    return session["role"] == role

def logout(wallet_address: str) -> bool:
    """
    Log out a wallet address.
    
    Args:
        wallet_address: The wallet address to log out
        
    Returns:
        bool: True if the wallet address was logged out successfully, False otherwise
    """
    wallet_address = wallet_address.lower()
    
    if wallet_address in authenticated_sessions:
        del authenticated_sessions[wallet_address]
        logger.info(f"Logged out {wallet_address}")
        return True
    
    return False

# Initialize the module
load_role_assignments()
