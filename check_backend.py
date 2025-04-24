import os
import sys
import importlib.util

def check_module(module_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} is available")
        return True
    except ImportError as e:
        print(f"❌ {module_name} is not available: {e}")
        return False

def check_backend():
    """Check if the backend components are working correctly"""
    print("Checking backend components...")
    
    # Check required modules
    modules = [
        "fastapi",
        "uvicorn",
        "web3",
        "ipfshttpclient",
        "cryptography",
        "streamlit",
        "pygroupsig"
    ]
    
    all_available = True
    for module in modules:
        if not check_module(module):
            all_available = False
    
    # Check backend modules
    try:
        from backend.crypto import aes, merkle
        print("✅ Backend crypto modules are available")
    except ImportError as e:
        print(f"❌ Backend crypto modules are not available: {e}")
        all_available = False
    
    # Try to import pygroupsig
    try:
        import pygroupsig
        print(f"✅ pygroupsig version: {getattr(pygroupsig, '__version__', 'unknown')}")
    except ImportError as e:
        print(f"❌ pygroupsig is not available: {e}")
        all_available = False
    
    # Check if the MCL library is available
    try:
        from pygroupsig.utils.mcl import G1
        g1 = G1.from_generator()
        print("✅ MCL library is working correctly")
    except Exception as e:
        print(f"❌ MCL library is not working: {e}")
        all_available = False
        print("Make sure you have set the MCL_LIB_PATH environment variable:")
        print("export MCL_LIB_PATH=$PWD/mcl/build/lib")
    
    # Check if the .env file exists
    if os.path.exists(".env"):
        print("✅ .env file exists")
    else:
        print("❌ .env file does not exist")
        all_available = False
    
    # Check if the contract artifacts exist
    if os.path.exists("artifacts/contracts/DataHub.sol/DataHub.json"):
        print("✅ Contract artifacts exist")
    else:
        print("❌ Contract artifacts do not exist")
        all_available = False
    
    # Final result
    if all_available:
        print("\n✅ All backend components are available!")
        return True
    else:
        print("\n❌ Some backend components are missing or not working correctly.")
        return False

if __name__ == "__main__":
    if check_backend():
        print("You can now run the backend with:")
        print("python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000")
    else:
        print("Please fix the issues before running the backend.")
        sys.exit(1)
