#!/bin/bash
# Script to run the contract test from WSL

set -e  # Exit on error

# Navigate to the project directory in WSL
cd /mnt/c/Users/pkhoa/OneDrive\ -\ VNU-HCMUS/Documents/SCHOOL/Khoá\ luận/main/healthcare-data-sharing

# Make the scripts executable
chmod +x run_contract_test.sh

# Run the test script
./run_contract_test.sh
