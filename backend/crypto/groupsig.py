import hashlib
import base64
import os
import json
import time
from pygroupsig import group, key

class GroupSignature:
    def __init__(self):
        # Initialize the group signature scheme (using CPY06 which supports revocation manager)
        self.scheme = "cpy06"

        # Create the group manager instance
        self.group_manager = group(self.scheme)()

        # Setup the group (generates keys)
        self.group_manager.setup()

        # Get the group key in base64 format for sharing
        self.group_key_b64 = self.group_manager.group_key.to_b64()

        # Create a member instance for signing
        self.member_group = group(self.scheme)()
        self.member_group.group_key.set_b64(self.group_key_b64)

        # Create a member key
        self.member_key = key(self.scheme, "member")()

        # Execute the join protocol
        msg2 = None
        seq = self.member_group.join_seq()
        for _ in range(0, seq + 1, 2):
            msg1 = self.group_manager.join_mgr(msg2)  # Group manager side
            msg2 = self.member_group.join_mem(msg1, self.member_key)  # Member side

    def sign(self, data):
        """Sign data with a group signature"""
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data, sort_keys=True)
        if isinstance(data, str):
            data = data.encode('utf-8')
            data = data.decode('utf-8')  # Convert back to string for pygroupsig

        # Sign the data using the member key
        result = self.member_group.sign(data, self.member_key)

        if result["status"] == "success":
            return result["signature"]
        else:
            raise Exception(f"Signing failed: {result.get('message', 'Unknown error')}")

    def verify(self, data, signature):
        """Verify a group signature"""
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data, sort_keys=True)
        if isinstance(data, str):
            data = data.encode('utf-8')
            data = data.decode('utf-8')  # Convert back to string for pygroupsig

        # Verify the signature
        result = self.member_group.verify(data, signature)

        return result["status"] == "success"

    def open(self, signature, group_manager_partial=None, revocation_manager_partial=None):
        """Open a group signature to reveal the signer"""
        # If no partial results are provided, return the group manager's partial result
        if group_manager_partial is None and revocation_manager_partial is None:
            result = self.group_manager.open(signature)
            return result

        # If only group manager's partial result is provided, return the revocation manager's partial result
        elif group_manager_partial is not None and revocation_manager_partial is None:
            result = self.group_manager.open(signature, group_manager_partial=group_manager_partial)
            return result

        # If both partial results are provided, complete the opening
        elif group_manager_partial is not None and revocation_manager_partial is not None:
            result = self.group_manager.open(
                signature,
                group_manager_partial=group_manager_partial,
                revocation_manager_partial=revocation_manager_partial
            )
            return result

        return {"status": "fail", "message": "Invalid parameters for opening"}

    def revoke(self, member_id):
        """Revoke a member from the group"""
        result = self.group_manager.reveal(member_id)
        return result["status"] == "success"

# Create a singleton instance
_instance = None

def initialize():
    """Initialize the group signature system"""
    global _instance
    if _instance is None:
        try:
            _instance = GroupSignature()
            return True
        except Exception as e:
            print(f"Error initializing group signature: {e}")
            return False
    return True

def sign(data):
    """Sign data with a group signature"""
    if not initialize():
        raise Exception("Failed to initialize group signature system")
    return _instance.sign(data)

def verify(data, signature):
    """Verify a group signature"""
    if not initialize():
        raise Exception("Failed to initialize group signature system")
    return _instance.verify(data, signature)

def open(signature, group_manager_partial=None, revocation_manager_partial=None):
    """Open a group signature to reveal the signer"""
    if not initialize():
        raise Exception("Failed to initialize group signature system")
    return _instance.open(signature, group_manager_partial, revocation_manager_partial)

def revoke(member_id):
    """Revoke a member from the group"""
    if not initialize():
        raise Exception("Failed to initialize group signature system")
    return _instance.revoke(member_id)
