#!/bin/bash

# Get the absolute path to the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the MCL_LIB_PATH environment variable to point to the mcl/build/lib directory
export MCL_LIB_PATH="$PROJECT_ROOT/mcl/build/lib"

# Add the MCL library path to LD_LIBRARY_PATH
export LD_LIBRARY_PATH="$PROJECT_ROOT/mcl/build/lib:$LD_LIBRARY_PATH"

echo "MCL_LIB_PATH set to: $MCL_LIB_PATH"
echo "LD_LIBRARY_PATH set to: $LD_LIBRARY_PATH"

# Run the FastAPI application
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
