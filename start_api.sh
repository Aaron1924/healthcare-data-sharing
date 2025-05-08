#!/bin/bash
set -e

# Check if keys exist, if not generate them
if [ ! -f /app/keys/group_public_key.b64 ]; then
    echo "Generating group signature keys..."
    python /app/generate_keys.py
else
    echo "Group signature keys already exist, skipping generation."
fi

# Start the API server
echo "Starting API server..."
exec uvicorn backend.api:app --host 0.0.0.0 --port 8000
