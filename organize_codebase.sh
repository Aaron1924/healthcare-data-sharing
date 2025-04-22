#!/bin/bash

# Create directories if they don't exist
mkdir -p scripts/utils
mkdir -p scripts/examples
mkdir -p scripts/tests

# Move utility scripts to scripts/utils
if [ -f check_mcl.py ]; then
    mv check_mcl.py scripts/utils/
fi

if [ -f check_backend.py ]; then
    mv check_backend.py scripts/utils/
fi

if [ -f test_ipfs.py ]; then
    mv test_ipfs.py scripts/utils/
fi

# Move key generation scripts to scripts
if [ -f cpy06_key_gen.py ]; then
    mv cpy06_key_gen.py scripts/
fi

# Move example scripts to scripts/examples
if [ -f test.py ]; then
    mv test.py scripts/examples/bbs04_example.py
fi

if [ -f test1.py ]; then
    mv test1.py scripts/examples/cpy06_example.py
fi

if [ -f Test_storing.py ]; then
    mv Test_storing.py scripts/examples/storing_example.py
fi

# Create local_storage directories
mkdir -p local_storage/records
mkdir -p local_storage/templates
mkdir -p local_storage/purchases
mkdir -p local_storage/transactions

echo "Codebase organization complete!"
echo "Unnecessary files moved to scripts directory."
echo "Local storage directories created."
