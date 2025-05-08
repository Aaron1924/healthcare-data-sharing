#!/usr/bin/env python3
"""
Script to generate all necessary keys for the group signature system.
This script should be run inside the Docker container.
"""

import os
import json
import base64
from pygroupsig import group, key

def main():
    """Generate all necessary keys for the group signature system."""
    print("Generating keys for the group signature system...")

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

    # Step 3: Save the group manager's key
    gm_key = {
        "xi1": str(g.manager_key.xi1),
        "xi2": str(g.manager_key.xi2),
        "gamma": str(g.manager_key.gamma)
    }
    with open("keys/group_manager_key.json", "w") as f:
        json.dump(gm_key, f, indent=2)
    print("Group manager key saved to keys/group_manager_key.json")

    # Step 4: Save the revocation manager's key
    rm_key = {
        "xi1": str(g.revocation_manager_key.xi1),
        "xi2": str(g.revocation_manager_key.xi2)
    }
    with open("keys/revocation_manager_key.json", "w") as f:
        json.dump(rm_key, f, indent=2)
    print("Revocation manager key saved to keys/revocation_manager_key.json")

    # Step 5: Create a member (doctor) and save their key
    # Create a member key
    mem_key = key("cpy06", "member")()

    # Use the join protocol
    msg2 = None
    seq = g.join_seq()
    for _ in range(0, seq + 1, 2):
        msg1 = g.join_mgr(msg2)  # Group manager side
        msg2 = g.join_mem(msg1, mem_key)  # Member side

    # Save the member key
    mem_key_b64 = mem_key.to_b64()
    with open("keys/doctor_member_key.b64", "w") as f:
        f.write(mem_key_b64)
    print(f"Doctor member key saved to keys/doctor_member_key.b64")

    print("\nAll keys generated successfully!")
    print("You can now use the group signature system.")

if __name__ == "__main__":
    main()
