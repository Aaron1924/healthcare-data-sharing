#!/usr/bin/env python3
"""
Script to check if group signature keys exist and generate them if they don't.
"""

import os
import sys
from generate_keys import main as generate_keys

def main():
    """Check if keys exist and generate them if they don't."""
    # Check if keys directory exists
    if not os.path.exists("keys"):
        print("Keys directory not found. Creating it...")
        os.makedirs("keys", exist_ok=True)
    
    # Check if group public key exists
    if not os.path.exists("keys/group_public_key.b64"):
        print("Group public key not found. Generating keys...")
        generate_keys()
    else:
        print("Group signature keys already exist.")

if __name__ == "__main__":
    main()
