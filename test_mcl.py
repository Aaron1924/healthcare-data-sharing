#!/usr/bin/env python3
"""
Test script to verify that mcl and pygroupsig are working correctly.
"""

import os
import sys
import time
import json

def test_mcl_env():
    """Test if MCL_LIB_PATH is set correctly."""
    mcl_lib_path = os.environ.get('MCL_LIB_PATH')
    print(f"MCL_LIB_PATH: {mcl_lib_path}")

    if not mcl_lib_path:
        print("ERROR: MCL_LIB_PATH environment variable is not set.")
        return False

    if not os.path.exists(mcl_lib_path):
        print(f"ERROR: MCL_LIB_PATH directory does not exist: {mcl_lib_path}")
        return False

    print(f"MCL_LIB_PATH directory exists: {mcl_lib_path}")

    # List files in the MCL_LIB_PATH directory
    print("Files in MCL_LIB_PATH directory:")
    for file in os.listdir(mcl_lib_path):
        print(f"  - {file}")

    return True

def test_pygroupsig_import():
    """Test if pygroupsig can be imported."""
    try:
        import pygroupsig
        print("Successfully imported pygroupsig module.")

        # Test basic functionality
        print("Testing basic pygroupsig functionality...")
        g = pygroupsig.group("bbs04")()
        g.setup()
        gk_b64 = g.group_key.to_b64()
        print(f"Group key generated: {gk_b64[:20]}...")

        return True
    except ImportError as e:
        print(f"ERROR: Failed to import pygroupsig module: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to use pygroupsig functionality: {e}")
        return False

def test_group_signature():
    """Test group signature functionality."""
    try:
        import pygroupsig

        # Check if keys directory exists
        if not os.path.exists("keys"):
            print("Keys directory not found. Creating it...")
            os.makedirs("keys", exist_ok=True)

            # Generate keys
            print("Generating group signature keys...")
            g = pygroupsig.group("cpy06")()
            g.setup()

            # Save group public key
            gk_b64 = g.group_key.to_b64()
            with open("keys/group_public_key.b64", "w") as f:
                f.write(gk_b64)
            print(f"Group public key saved: {gk_b64[:20]}...")

            # Save group manager key
            gm_key = {
                "xi1": str(g.manager_key.xi1),
                "xi2": str(g.manager_key.xi2),
                "gamma": str(g.manager_key.gamma)
            }
            with open("keys/group_manager_key.json", "w") as f:
                json.dump(gm_key, f, indent=2)
            print("Group manager key saved.")

            # Create and save member key
            mem_key = g.join(g.manager_key)
            mem_key_b64 = mem_key.to_b64()
            with open("keys/doctor_member_key.b64", "w") as f:
                f.write(mem_key_b64)
            print("Doctor member key saved.")

        # Load group public key
        with open("keys/group_public_key.b64", "r") as f:
            group_key_b64 = f.read().strip()

        # Create member group
        member_group = pygroupsig.group("cpy06")()
        member_group.group_key.set_b64(group_key_b64)

        # Load member key
        with open("keys/doctor_member_key.b64", "r") as f:
            member_key_b64 = f.read().strip()

        member_key = pygroupsig.key("cpy06", "member")()
        member_key.set_b64(member_key_b64)

        # Test signing and verification
        message = f"Test message {int(time.time())}"
        signature = member_group.sign(message, member_key)

        print(f"Signature created: {str(signature)[:20]}...")

        # Verify signature
        verified = member_group.verify(message, signature)
        print(f"Signature verification result: {verified}")

        return verified
    except Exception as e:
        print(f"ERROR: Error in group signature test: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing MCL and pygroupsig ===")

    mcl_ok = test_mcl_env()
    pygroupsig_ok = test_pygroupsig_import()
    sig_ok = test_group_signature()

    print("\n=== Test Summary ===")
    print(f"MCL Environment: {'SUCCESS' if mcl_ok else 'FAILURE'}")
    print(f"pygroupsig Import: {'SUCCESS' if pygroupsig_ok else 'FAILURE'}")
    print(f"Group Signature: {'SUCCESS' if sig_ok else 'FAILURE'}")

    if mcl_ok and pygroupsig_ok and sig_ok:
        print("\nSUCCESS: MCL and pygroupsig are working correctly!")
        sys.exit(0)
    else:
        print("\nFAILURE: There were issues with MCL or pygroupsig.")
        sys.exit(1)
