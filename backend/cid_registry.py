"""
CID Registry module for tracking IPFS CIDs without relying on IPFS pin listing.
"""

import os
import json
import time
from typing import List, Dict, Optional, Set

# Registry file path
REGISTRY_DIR = "local_storage"
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "cid_registry.json")

# Ensure the registry directory exists
os.makedirs(REGISTRY_DIR, exist_ok=True)

def load_registry() -> Dict:
    """Load the CID registry from disk"""
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading CID registry: {e}")
            return {"cids": {}, "patient_cids": {}, "doctor_cids": {}, "metadata": {"last_updated": time.time()}}
    else:
        return {"cids": {}, "patient_cids": {}, "doctor_cids": {}, "metadata": {"last_updated": time.time()}}

def save_registry(registry: Dict) -> None:
    """Save the CID registry to disk"""
    try:
        # Update the last_updated timestamp
        registry["metadata"]["last_updated"] = time.time()
        
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"Error saving CID registry: {e}")

def register_cid(cid: str, owner_address: Optional[str] = None, record_type: str = "record", metadata: Optional[Dict] = None) -> None:
    """
    Register a CID in the local registry
    
    Args:
        cid: The IPFS CID
        owner_address: The wallet address of the owner (patient or doctor)
        record_type: The type of record (e.g., "record", "sharing", "template")
        metadata: Additional metadata to store with the CID
    """
    registry = load_registry()
    
    # Add the CID to the registry if it doesn't exist
    if cid not in registry["cids"]:
        registry["cids"][cid] = {
            "timestamp": time.time(),
            "owner": owner_address,
            "type": record_type,
            "metadata": metadata or {}
        }
    
    # Add the CID to the patient's list if owner_address is provided
    if owner_address:
        if owner_address.startswith("0x"):  # It's a wallet address
            # Check if it's a patient or doctor based on the record_type
            if record_type in ["record", "template"]:
                if owner_address not in registry["patient_cids"]:
                    registry["patient_cids"][owner_address] = []
                if cid not in registry["patient_cids"][owner_address]:
                    registry["patient_cids"][owner_address].append(cid)
            elif record_type == "sharing":
                if owner_address not in registry["doctor_cids"]:
                    registry["doctor_cids"][owner_address] = []
                if cid not in registry["doctor_cids"][owner_address]:
                    registry["doctor_cids"][owner_address].append(cid)
    
    # Save the updated registry
    save_registry(registry)

def get_patient_cids(patient_address: str) -> List[str]:
    """
    Get all CIDs owned by a patient
    
    Args:
        patient_address: The wallet address of the patient
        
    Returns:
        A list of CIDs owned by the patient
    """
    registry = load_registry()
    return registry["patient_cids"].get(patient_address, [])

def get_doctor_cids(doctor_address: str) -> List[str]:
    """
    Get all CIDs shared with a doctor
    
    Args:
        doctor_address: The wallet address of the doctor
        
    Returns:
        A list of CIDs shared with the doctor
    """
    registry = load_registry()
    return registry["doctor_cids"].get(doctor_address, [])

def get_all_cids() -> List[str]:
    """
    Get all CIDs in the registry
    
    Returns:
        A list of all CIDs
    """
    registry = load_registry()
    return list(registry["cids"].keys())

def get_cid_info(cid: str) -> Optional[Dict]:
    """
    Get information about a CID
    
    Args:
        cid: The IPFS CID
        
    Returns:
        A dictionary with information about the CID, or None if the CID is not in the registry
    """
    registry = load_registry()
    return registry["cids"].get(cid)

def cid_exists(cid: str) -> bool:
    """
    Check if a CID exists in the registry
    
    Args:
        cid: The IPFS CID
        
    Returns:
        True if the CID exists in the registry, False otherwise
    """
    registry = load_registry()
    return cid in registry["cids"]

def remove_cid(cid: str) -> bool:
    """
    Remove a CID from the registry
    
    Args:
        cid: The IPFS CID
        
    Returns:
        True if the CID was removed, False otherwise
    """
    registry = load_registry()
    
    if cid in registry["cids"]:
        # Get the owner of the CID
        owner = registry["cids"][cid].get("owner")
        
        # Remove the CID from the registry
        del registry["cids"][cid]
        
        # Remove the CID from the patient's list if it's there
        if owner and owner in registry["patient_cids"] and cid in registry["patient_cids"][owner]:
            registry["patient_cids"][owner].remove(cid)
        
        # Remove the CID from the doctor's list if it's there
        if owner and owner in registry["doctor_cids"] and cid in registry["doctor_cids"][owner]:
            registry["doctor_cids"][owner].remove(cid)
        
        # Save the updated registry
        save_registry(registry)
        return True
    
    return False
