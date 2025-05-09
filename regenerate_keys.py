#!/usr/bin/env python3
"""
Script to regenerate group signature keys in the correct format.
"""

import os
import json
from pygroupsig import group, key

def extract_number(value_str):
    """Extract the numeric part from a string like '<class 'pygroupsig.utils.mcl.Fr'> 123456...'"""
    if '<class' in value_str:
        return value_str.split('> ')[1]
    return value_str

def main():
    print("Regenerating group signature keys...")
    
    # Create keys directory if it doesn't exist
    os.makedirs("keys", exist_ok=True)
    
    # Initialize the group with CPY06 scheme
    g = group("cpy06")()
    g.setup()
    
    # Get and save the group public key
    gk_b64 = g.group_key.to_b64()
    print(f"\nGroup public key generated: {gk_b64[:20]}...")
    
    # Save group public key
    with open("keys/group_public_key.b64", "w") as f:
        f.write(gk_b64)
    print("Group public key saved to keys/group_public_key.b64")
    
    # Save the group manager's key with proper numeric format
    gm_key = {
        "xi1": str(g.manager_key.xi1.get_str()),
        "xi2": str(g.manager_key.xi2.get_str()),
        "gamma": str(g.manager_key.gamma.get_str())
    }
    
    with open("keys/group_manager_key.json", "w") as f:
        json.dump(gm_key, f, indent=2)
    print("Group manager key saved to keys/group_manager_key.json")
    
    # Save the revocation manager's key with proper numeric format
    rm_key = {
        "xi1": str(g.revocation_manager_key.xi1.get_str()),
        "xi2": str(g.revocation_manager_key.xi2.get_str())
    }
    
    with open("keys/revocation_manager_key.json", "w") as f:
        json.dump(rm_key, f, indent=2)
    print("Revocation manager key saved to keys/revocation_manager_key.json")
    
    # Create a member (doctor) key
    member_group = group("cpy06")()
    member_group.group_key.set_b64(gk_b64)
    
    member_key = key("cpy06", "member")()
    
    # Execute the join protocol
    msg2 = None
    seq = member_group.join_seq()
    for i in range(0, seq + 1, 2):
        msg1 = g.join_mgr(msg2)  # Group manager side
        msg2 = member_group.join_mem(msg1, member_key)  # Member side
    
    # Save the member key
    member_key_b64 = member_key.to_b64()
    with open("keys/doctor_member_key.b64", "w") as f:
        f.write(member_key_b64)
    print("Doctor member key saved to keys/doctor_member_key.b64")
    
    # Try to fix existing keys if regeneration fails
    try:
        # Try to fix existing group manager key
        if os.path.exists("keys/group_manager_key.json.bak"):
            print("\nAttempting to fix existing group manager key...")
            with open("keys/group_manager_key.json.bak", "r") as f:
                old_gm_key = json.load(f)
            
            fixed_gm_key = {
                "xi1": extract_number(old_gm_key["xi1"]),
                "xi2": extract_number(old_gm_key["xi2"]),
                "gamma": extract_number(old_gm_key["gamma"])
            }
            
            with open("keys/group_manager_key.json", "w") as f:
                json.dump(fixed_gm_key, f, indent=2)
            print("Fixed group manager key saved.")
        
        # Try to fix existing revocation manager key
        if os.path.exists("keys/revocation_manager_key.json.bak"):
            print("Attempting to fix existing revocation manager key...")
            with open("keys/revocation_manager_key.json.bak", "r") as f:
                old_rm_key = json.load(f)
            
            fixed_rm_key = {
                "xi1": extract_number(old_rm_key["xi1"]),
                "xi2": extract_number(old_rm_key["xi2"])
            }
            
            with open("keys/revocation_manager_key.json", "w") as f:
                json.dump(fixed_rm_key, f, indent=2)
            print("Fixed revocation manager key saved.")
    except Exception as e:
        print(f"Error fixing existing keys: {e}")
    
    print("\nKey regeneration complete!")

if __name__ == "__main__":
    main()
