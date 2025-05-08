#!/usr/bin/env python3
"""
Script to fix the group signature keys for the healthcare data sharing application.
This script corrects the format of the keys in the JSON files.
"""

import os
import json
import sys

def fix_keys():
    """Fix the group signature keys."""
    print("Fixing group signature keys...")

    # Check if keys directory exists
    if not os.path.exists("keys"):
        print("Keys directory not found. Please run cpy06_key_gen.py first.")
        return False

    # Fix group manager key
    try:
        gm_key_path = "keys/group_manager_key.json"
        if os.path.exists(gm_key_path):
            with open(gm_key_path, "r") as f:
                gm_key = json.load(f)
            
            # Check if keys need fixing (contain class name)
            needs_fixing = False
            for key in ["xi1", "xi2", "gamma"]:
                if key in gm_key and isinstance(gm_key[key], str) and "<class" in gm_key[key]:
                    needs_fixing = True
                    # Extract the number from the string
                    gm_key[key] = gm_key[key].split()[-1]
            
            if needs_fixing:
                # Save the fixed key
                with open(gm_key_path, "w") as f:
                    json.dump(gm_key, f, indent=2)
                print(f"Fixed group manager key: {gm_key_path}")
            else:
                print(f"Group manager key already in correct format: {gm_key_path}")
        else:
            print(f"Group manager key not found: {gm_key_path}")
    except Exception as e:
        print(f"Error fixing group manager key: {e}")
        return False

    # Fix revocation manager key
    try:
        rm_key_path = "keys/revocation_manager_key.json"
        if os.path.exists(rm_key_path):
            with open(rm_key_path, "r") as f:
                rm_key = json.load(f)
            
            # Check if keys need fixing (contain class name)
            needs_fixing = False
            for key in ["xi1", "xi2"]:
                if key in rm_key and isinstance(rm_key[key], str) and "<class" in rm_key[key]:
                    needs_fixing = True
                    # Extract the number from the string
                    rm_key[key] = rm_key[key].split()[-1]
            
            if needs_fixing:
                # Save the fixed key
                with open(rm_key_path, "w") as f:
                    json.dump(rm_key, f, indent=2)
                print(f"Fixed revocation manager key: {rm_key_path}")
            else:
                print(f"Revocation manager key already in correct format: {rm_key_path}")
        else:
            print(f"Revocation manager key not found: {rm_key_path}")
    except Exception as e:
        print(f"Error fixing revocation manager key: {e}")
        return False

    print("Group signature keys fixed successfully.")
    return True

if __name__ == "__main__":
    if fix_keys():
        sys.exit(0)
    else:
        sys.exit(1)
