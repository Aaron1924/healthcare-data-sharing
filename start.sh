#!/bin/bash
# Script to start the healthcare API server with proper initialization

# Fix the group signature keys
echo "Fixing group signature keys..."
python fix_keys.py

# Start the API server
echo "Starting API server..."
uvicorn backend.api:app --host 0.0.0.0 --port 8000
