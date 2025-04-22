#!/usr/bin/env python3
import os
import sys
import subprocess

def check_mcl_env():
    """Check if the MCL_LIB_PATH environment variable is set"""
    mcl_lib_path = os.environ.get("MCL_LIB_PATH")
    if mcl_lib_path:
        print(f"MCL_LIB_PATH is set to: {mcl_lib_path}")
        
        # Check if the directory exists
        if os.path.isdir(mcl_lib_path):
            print(f"✅ Directory exists: {mcl_lib_path}")
            
            # Check if the library files exist
            lib_files = [
                "libmcl.so",
                "libmclbn384_256.so",
                "libmclbn384.so",
                "libmclbn512.so"
            ]
            
            all_found = True
            for lib_file in lib_files:
                lib_path = os.path.join(mcl_lib_path, lib_file)
                if os.path.isfile(lib_path):
                    print(f"✅ Found library: {lib_file}")
                else:
                    print(f"❌ Missing library: {lib_file}")
                    all_found = False
            
            if all_found:
                print("\n✅ MCL library is properly set up!")
                return True
            else:
                print("\n❌ Some MCL library files are missing.")
                return False
        else:
            print(f"❌ Directory does not exist: {mcl_lib_path}")
            return False
    else:
        print("❌ MCL_LIB_PATH environment variable is not set.")
        return False

def build_mcl():
    """Build the MCL library"""
    print("Building MCL library...")
    
    # Check if git is available
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        print("❌ Git is not available. Please install Git.")
        return False
    
    # Check if cmake is available
    try:
        subprocess.run(["cmake", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        print("❌ CMake is not available. Please install CMake.")
        return False
    
    # Check if make is available
    try:
        subprocess.run(["make", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        print("❌ Make is not available. Please install Make.")
        return False
    
    # Clone the MCL repository
    if not os.path.exists("mcl"):
        print("Cloning MCL repository...")
        try:
            subprocess.run(["git", "clone", "https://github.com/herumi/mcl.git"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to clone MCL repository: {e}")
            return False
    else:
        print("MCL repository already exists.")
    
    # Build MCL
    try:
        print("Building MCL...")
        subprocess.run(["cmake", "-B", "build", "."], check=True, cwd="mcl")
        subprocess.run(["make", "-C", "build"], check=True, cwd="mcl")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build MCL: {e}")
        return False
    
    # Set the MCL_LIB_PATH environment variable
    mcl_lib_path = os.path.abspath(os.path.join("mcl", "build", "lib"))
    os.environ["MCL_LIB_PATH"] = mcl_lib_path
    print(f"Set MCL_LIB_PATH to: {mcl_lib_path}")
    
    # Check if the build was successful
    return check_mcl_env()

def main():
    """Main function"""
    print("Checking MCL library setup...")
    
    if check_mcl_env():
        print("MCL library is already set up correctly.")
        return 0
    
    print("\nMCL library is not set up correctly.")
    
    # Ask if the user wants to build MCL
    while True:
        response = input("Do you want to build the MCL library now? (y/n): ").lower()
        if response in ["y", "yes"]:
            if build_mcl():
                print("\n✅ MCL library has been built successfully!")
                print("\nTo permanently set the MCL_LIB_PATH environment variable, add the following line to your shell profile:")
                print(f"export MCL_LIB_PATH={os.environ.get('MCL_LIB_PATH')}")
                return 0
            else:
                print("\n❌ Failed to build MCL library.")
                return 1
        elif response in ["n", "no"]:
            print("\nPlease set up the MCL library manually:")
            print("1. Clone the MCL repository: git clone https://github.com/herumi/mcl.git")
            print("2. Build MCL: cd mcl && cmake -B build . && make -C build")
            print("3. Set the MCL_LIB_PATH environment variable: export MCL_LIB_PATH=$PWD/mcl/build/lib")
            return 1
        else:
            print("Please enter 'y' or 'n'.")

if __name__ == "__main__":
    sys.exit(main())
