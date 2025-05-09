#!/usr/bin/env python3
"""
Script to run the FastAPI application with the correct MCL library path.
"""

import os
import sys
import subprocess
import uvicorn

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Set the MCL_LIB_PATH environment variable to point to the mcl/build/lib directory
mcl_lib_path = os.path.join(project_root, "mcl", "build", "lib")
os.environ["MCL_LIB_PATH"] = mcl_lib_path

# Add the MCL library path to LD_LIBRARY_PATH
if "LD_LIBRARY_PATH" in os.environ:
    os.environ["LD_LIBRARY_PATH"] = f"{mcl_lib_path}:{os.environ['LD_LIBRARY_PATH']}"
else:
    os.environ["LD_LIBRARY_PATH"] = mcl_lib_path

print(f"MCL_LIB_PATH set to: {os.environ.get('MCL_LIB_PATH')}")
print(f"LD_LIBRARY_PATH set to: {os.environ.get('LD_LIBRARY_PATH')}")

# Run the FastAPI application
if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
