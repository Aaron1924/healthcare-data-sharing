#!/usr/bin/env python3
"""
Run the key generation script for the healthcare data sharing application.
"""

import os
import sys
import subprocess

def main():
    print("Running key generation for healthcare data sharing application...")
    
    # Check if pygroupsig is installed
    try:
        import pygroupsig
        print("pygroupsig is installed.")
    except ImportError:
        print("Error: pygroupsig is not installed.")
        print("Please make sure the pygroupsig module is properly installed.")
        sys.exit(1)
    
    # Run the key generation script
    try:
        subprocess.run([sys.executable, "generate_keys.py"], check=True)
        print("Key generation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running key generation script: {e}")
        sys.exit(1)
    
    # Check if keys were generated
    if os.path.exists("keys") and os.path.isdir("keys"):
        key_files = os.listdir("keys")
        if key_files:
            print(f"Generated {len(key_files)} key files:")
            for file in key_files:
                print(f"  - {file}")
        else:
            print("Warning: No key files were generated.")
    else:
        print("Error: Keys directory was not created.")
        sys.exit(1)
    
    print("\nKey generation process completed.")
    print("You can now run the application with group signature support.")

if __name__ == "__main__":
    main()
