#!/usr/bin/env python3
"""
Script to fix the format of existing group signature keys.
"""

import os
import json
import shutil

def extract_number(value_str):
    """Extract the numeric part from a string like '<class 'pygroupsig.utils.mcl.Fr'> 123456...'"""
    if '<class' in value_str:
        return value_str.split('> ')[1]
    return value_str

def main():
    print("Fixing group signature keys...")
    
    # Backup existing keys
    if os.path.exists("keys/group_manager_key.json"):
        shutil.copy("keys/group_manager_key.json", "keys/group_manager_key.json.bak")
        
        # Fix group manager key
        with open("keys/group_manager_key.json", "r") as f:
            gm_key = json.load(f)
        
        fixed_gm_key = {
            "xi1": extract_number(gm_key["xi1"]),
            "xi2": extract_number(gm_key["xi2"]),
            "gamma": extract_number(gm_key["gamma"])
        }
        
        with open("keys/group_manager_key.json", "w") as f:
            json.dump(fixed_gm_key, f, indent=2)
        print("Fixed group manager key saved.")
    
    if os.path.exists("keys/revocation_manager_key.json"):
        shutil.copy("keys/revocation_manager_key.json", "keys/revocation_manager_key.json.bak")
        
        # Fix revocation manager key
        with open("keys/revocation_manager_key.json", "r") as f:
            rm_key = json.load(f)
        
        fixed_rm_key = {
            "xi1": extract_number(rm_key["xi1"]),
            "xi2": extract_number(rm_key["xi2"])
        }
        
        with open("keys/revocation_manager_key.json", "w") as f:
            json.dump(fixed_rm_key, f, indent=2)
        print("Fixed revocation manager key saved.")
    
    print("\nKey fixing complete!")

if __name__ == "__main__":
    main()
