#!/usr/bin/env python3
"""
Test script to verify that mcl and pygroupsig are working correctly.
"""

import os
import sys

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

if __name__ == "__main__":
    print("Testing MCL and pygroupsig...")
    
    mcl_ok = test_mcl_env()
    pygroupsig_ok = test_pygroupsig_import()
    
    if mcl_ok and pygroupsig_ok:
        print("\nSUCCESS: MCL and pygroupsig are working correctly!")
        sys.exit(0)
    else:
        print("\nFAILURE: There were issues with MCL or pygroupsig.")
        sys.exit(1)
