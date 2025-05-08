"""
Helper functions for IPFS operations that work around protobuf compatibility issues.
"""

import requests
import json
import os

def get_ipfs_pins(ipfs_api_url="http://localhost:5001/api/v0"):
    """
    Get the list of pinned items from IPFS using direct HTTP API calls.
    This bypasses the protobuf compatibility issues in ipfshttpclient.
    
    Args:
        ipfs_api_url: The URL of the IPFS API
        
    Returns:
        list: A list of CIDs that are pinned in IPFS
    """
    try:
        # Make a direct HTTP request to the IPFS API
        response = requests.post(f"{ipfs_api_url}/pin/ls")
        
        if response.status_code == 200:
            # Parse the JSON response
            result = response.json()
            
            # Extract the keys (CIDs)
            if "Keys" in result:
                return list(result["Keys"].keys())
            else:
                print("No pins found in IPFS")
                return []
        else:
            print(f"Error getting pins from IPFS: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception getting pins from IPFS: {str(e)}")
        return []

def get_all_records(local_storage_path="local_storage"):
    """
    Get a list of all records from both IPFS and local storage.
    
    Args:
        local_storage_path: Path to the local storage directory
        
    Returns:
        list: A list of CIDs from both IPFS and local storage
    """
    records = []
    
    # Get records from IPFS
    ipfs_records = get_ipfs_pins()
    records.extend(ipfs_records)
    
    # Get records from local storage
    if os.path.exists(local_storage_path):
        for file_name in os.listdir(local_storage_path):
            if os.path.isfile(os.path.join(local_storage_path, file_name)):
                if file_name not in records:  # Avoid duplicates
                    records.append(file_name)
    
    return records

def pin_to_ipfs(cid, ipfs_api_url="http://localhost:5001/api/v0"):
    """
    Pin a CID to IPFS using direct HTTP API calls.
    This bypasses the protobuf compatibility issues in ipfshttpclient.
    
    Args:
        cid: The CID to pin
        ipfs_api_url: The URL of the IPFS API
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make a direct HTTP request to the IPFS API
        response = requests.post(f"{ipfs_api_url}/pin/add?arg={cid}")
        
        if response.status_code == 200:
            print(f"Successfully pinned {cid} using direct HTTP API")
            return True
        else:
            print(f"Error pinning {cid} to IPFS: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception pinning {cid} to IPFS: {str(e)}")
        return False
