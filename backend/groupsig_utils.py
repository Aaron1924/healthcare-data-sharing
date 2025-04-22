"""
Utility functions for group signatures in the healthcare data sharing application.
"""

import os
import json
from pygroupsig import group, key

class GroupSignatureManager:
    def __init__(self):
        """Initialize the group signature manager."""
        self.g = None  # Group manager's group instance
        self.gm = None  # Doctor's group instance
        self.doctor_mk = None  # Doctor's member key

        # Load keys
        self._load_keys()

    def _load_keys(self):
        """Load keys from files."""
        try:
            # Check if keys directory exists
            if not os.path.exists("keys"):
                print("Keys directory not found. Please run bbs04_key_gen.py first.")
                return False

            # Load group public key
            with open("keys/group_public_key.b64", "r") as f:
                group_key_b64 = f.read().strip()

            # Initialize group manager's group instance
            self.g = group("cpy06")()
            self.g.setup()

            # Load group manager's secret key
            with open("keys/group_manager_key.json", "r") as f:
                gm_key = json.load(f)
                # Convert string representations back to the appropriate type
                # Note: In a real implementation, we would need to handle this conversion properly
                # For demo purposes, we'll use placeholder values
                self.g.manager_key.xi1 = gm_key["xi1"]
                self.g.manager_key.xi2 = gm_key["xi2"]
                self.g.manager_key.gamma = gm_key["gamma"]

            # Load revocation manager's secret key
            with open("keys/revocation_manager_key.json", "r") as f:
                rm_key = json.load(f)
                self.g.revocation_manager_key.xi1 = rm_key["xi1"]
                self.g.revocation_manager_key.xi2 = rm_key["xi2"]

            # Initialize doctor's group instance
            self.gm = group("cpy06")()
            self.gm.group_key.set_b64(group_key_b64)

            # Load doctor's member key
            with open("keys/doctor_member_key.b64", "r") as f:
                doctor_key_b64 = f.read().strip()
                self.doctor_mk = key("cpy06", "member")()
                self.doctor_mk.set_b64(doctor_key_b64)

            print("Group signature keys loaded successfully.")
            return True
        except Exception as e:
            print(f"Error loading group signature keys: {e}")
            return False

    def sign(self, message):
        """Sign a message using the doctor's member key."""
        if not self.gm or not self.doctor_mk:
            print("Group signature manager not properly initialized.")
            return None

        try:
            s_msg = self.gm.sign(message, self.doctor_mk)
            return s_msg["signature"]
        except Exception as e:
            print(f"Error signing message: {e}")
            return None

    def verify(self, message, signature):
        """Verify a signature."""
        if not self.gm:
            print("Group signature manager not properly initialized.")
            return False

        try:
            return self.gm.verify(message, signature)
        except Exception as e:
            print(f"Error verifying signature: {e}")
            return False

    def open_group_manager(self, signature):
        """Perform partial opening as the group manager."""
        if not self.g:
            print("Group signature manager not properly initialized.")
            return None

        try:
            partial_g_result = self.g.open(signature)
            return partial_g_result["partial_g"]
        except Exception as e:
            print(f"Error performing group manager partial opening: {e}")
            return None

    def open_revocation_manager(self, signature, partial_g):
        """Perform partial opening as the revocation manager."""
        if not self.g:
            print("Group signature manager not properly initialized.")
            return None

        try:
            partial_r_result = self.g.open(signature, group_manager_partial=partial_g)
            return partial_r_result["partial_r"]
        except Exception as e:
            print(f"Error performing revocation manager partial opening: {e}")
            return None

    def open_full(self, signature, partial_g, partial_r):
        """Perform full opening of a signature."""
        if not self.g:
            print("Group signature manager not properly initialized.")
            return None

        try:
            full_open_result = self.g.open(
                signature,
                group_manager_partial=partial_g,
                revocation_manager_partial=partial_r
            )
            return full_open_result
        except Exception as e:
            print(f"Error performing full opening: {e}")
            return None

# Singleton instance
gsm = GroupSignatureManager()

def sign_message(message):
    """Sign a message using the doctor's member key."""
    return gsm.sign(message)

def verify_signature(message, signature):
    """Verify a signature."""
    return gsm.verify(message, signature)

def open_signature_group_manager(signature):
    """Perform partial opening as the group manager."""
    return gsm.open_group_manager(signature)

def open_signature_revocation_manager(signature, partial_g):
    """Perform partial opening as the revocation manager."""
    return gsm.open_revocation_manager(signature, partial_g)

def open_signature_full(signature, partial_g, partial_r):
    """Perform full opening of a signature."""
    return gsm.open_full(signature, partial_g, partial_r)
