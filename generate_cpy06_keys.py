#!/usr/bin/env python3
"""
Key generation script for CPY06 group signature scheme.
This script generates all necessary keys for the healthcare data sharing application.
"""

import os
import json
import time
from pygroupsig import group, key

def generate_keys():
    """Generate all necessary keys for the CPY06 group signature scheme."""
    print("Generating keys for the CPY06 group signature scheme...")

    # Create keys directory
    os.makedirs("keys", exist_ok=True)

    # Step 1: Initialize the group with CPY06 scheme
    g = group("cpy06")()
    g.setup()

    # Step 2: Get and save the group public key
    gk_b64 = g.group_key.to_b64()
    print(f"\nGroup public key generated: {gk_b64[:20]}...")

    # Save group public key
    with open("keys/group_public_key.b64", "w") as f:
        f.write(gk_b64)
    print("Group public key saved to keys/group_public_key.b64")

    # Step 3: Extract and save the group manager's secret key
    print("\nExtracting group manager's secret key...")
    # For CPY06, we need to save the components separately
    gm_key = {
        "xi1": str(g.manager_key.xi1),
        "xi2": str(g.manager_key.xi2),
        "gamma": str(g.manager_key.gamma)
    }

    # Save group manager key
    with open("keys/group_manager_key.json", "w") as f:
        json.dump(gm_key, f, indent=2)
    print("Group manager key saved to keys/group_manager_key.json")

    # Step 4: Extract and save the revocation manager's secret key
    print("\nExtracting revocation manager's secret key...")
    rm_key = {
        "xi1": str(g.revocation_manager_key.xi1),
        "xi2": str(g.revocation_manager_key.xi2)
    }

    # Save revocation manager key
    with open("keys/revocation_manager_key.json", "w") as f:
        json.dump(rm_key, f, indent=2)
    print("Revocation manager key saved to keys/revocation_manager_key.json")

    # Step 5: Create client-side group for doctor
    print("\nCreating client-side group for doctor...")
    gm = group("cpy06")()
    gm.group_key.set_b64(gk_b64)

    # Create a member key for the doctor
    print("Creating doctor's member key...")
    mk = key("cpy06", "member")()

    # Execute the join protocol
    print("Executing join protocol...")
    try:
        # Use the join method directly if available
        mem_key = g.join(g.manager_key)
        mem_key_b64 = mem_key.to_b64()
        print("Used direct join method to create member key")
    except Exception as e:
        print(f"Direct join failed: {e}")
        print("Falling back to join_seq protocol...")
        
        # Execute the join protocol using join_seq
        msg2 = None
        seq = gm.join_seq()
        for i in range(0, seq + 1, 2):
            print(f"Join protocol step {i}/{seq}")
            msg1 = g.join_mgr(msg2)  # Group manager side
            if i < seq:  # Only do the member side if we're not at the last step
                msg2 = gm.join_mem(msg1, mk)  # Member (doctor) side
        
        # Get the member key
        mem_key_b64 = mk.to_b64()
        print("Used join_seq protocol to create member key")

    # Save doctor's member key
    with open("keys/doctor_member_key.b64", "w") as f:
        f.write(mem_key_b64)
    print("Doctor's member key saved to keys/doctor_member_key.b64")

    # Step 6: Test signing
    print("\nTesting signing...")
    test_message = "Test medical record"
    
    # Create a new group instance for signing
    sign_group = group("cpy06")()
    sign_group.group_key.set_b64(gk_b64)
    
    # Load the member key
    sign_mk = key("cpy06", "member")()
    sign_mk.set_b64(mem_key_b64)
    
    # Sign the test message
    try:
        s_msg = sign_group.sign(test_message, sign_mk)
        print(f"Signature created successfully")
        
        # Test verification
        if isinstance(s_msg, dict) and "signature" in s_msg:
            signature = s_msg["signature"]
        else:
            signature = s_msg
            
        v_result = sign_group.verify(test_message, signature)
        print(f"Verification result: {v_result}")
        
        if v_result:
            print("Signature verification successful!")
        else:
            print("Signature verification failed!")
    except Exception as e:
        print(f"Error during signing/verification test: {e}")

    print("\nAll keys generated and saved successfully!")
    print("Files created:")
    print("  - keys/group_public_key.b64")
    print("  - keys/group_manager_key.json")
    print("  - keys/revocation_manager_key.json")
    print("  - keys/doctor_member_key.b64")
    
    return True

if __name__ == "__main__":
    generate_keys()
