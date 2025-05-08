"""
IPFS CLI wrapper module to interact with IPFS daemon directly using subprocess.
This bypasses the version compatibility issues with ipfshttpclient.
"""

import subprocess
import os
import json
import tempfile
from typing import List, Dict, Optional, Union, BinaryIO

def run_ipfs_command(args: List[str]) -> Dict:
    """
    Run an IPFS command using subprocess

    Args:
        args: List of command arguments (without 'ipfs' prefix)

    Returns:
        Dict with keys:
            - success: Boolean indicating if the command was successful
            - output: Command output if successful
            - error: Error message if not successful
    """
    try:
        # Construct the full command with 'ipfs' prefix
        cmd = ["ipfs"] + args

        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                "success": True,
                "output": result.stdout.strip()
            }
        else:
            return {
                "success": False,
                "error": result.stderr.strip() or "Unknown error"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_ipfs_pins() -> List[str]:
    """
    Get the list of pinned items from IPFS using the CLI

    Returns:
        List of CIDs that are pinned in IPFS
    """
    result = run_ipfs_command(["pin", "ls", "--type=recursive"])

    if result["success"]:
        # Parse the output to get the CIDs
        pins = []
        for line in result["output"].splitlines():
            parts = line.split()
            if len(parts) >= 1:
                pins.append(parts[0])
        return pins
    else:
        print(f"Error getting pins from IPFS CLI: {result['error']}")
        return []

def add_to_ipfs(data: Union[bytes, str, BinaryIO], is_file: bool = False) -> Dict:
    """
    Add data to IPFS using the CLI

    Args:
        data: The data to add (bytes, string, or file-like object)
        is_file: Whether the data is a file path

    Returns:
        Dict with keys:
            - success: Boolean indicating if the add was successful
            - cid: The CID of the added data if successful
            - error: Error message if not successful
    """
    try:
        if is_file:
            # Data is a file path
            result = run_ipfs_command(["add", "-Q", data])
        else:
            # Data is bytes or string
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                if isinstance(data, str):
                    temp.write(data.encode())
                else:
                    temp.write(data)
                temp.flush()
                temp_path = temp.name

            # Add the temporary file to IPFS
            result = run_ipfs_command(["add", "-Q", temp_path])

            # Clean up the temporary file
            os.unlink(temp_path)

        if result["success"]:
            return {
                "success": True,
                "cid": result["output"].strip()
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def pin_to_ipfs(cid: str) -> Dict:
    """
    Pin a CID to IPFS using the CLI

    Args:
        cid: The CID to pin

    Returns:
        Dict with keys:
            - success: Boolean indicating if the pin was successful
            - error: Error message if not successful
    """
    result = run_ipfs_command(["pin", "add", cid])

    if result["success"]:
        return {
            "success": True
        }
    else:
        return {
            "success": False,
            "error": result["error"]
        }

def cat_from_ipfs(cid: str) -> Dict:
    """
    Retrieve data from IPFS using the CLI

    Args:
        cid: The CID to retrieve

    Returns:
        Dict with keys:
            - success: Boolean indicating if the retrieval was successful
            - data: The retrieved data if successful (as bytes)
            - error: Error message if not successful
    """
    try:
        # Use subprocess directly to get binary data
        cmd = ["ipfs", "cat", cid]
        result = subprocess.run(cmd, capture_output=True)

        if result.returncode == 0:
            return {
                "success": True,
                "data": result.stdout  # This is binary data
            }
        else:
            return {
                "success": False,
                "error": result.stderr.decode('utf-8', errors='replace')
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def is_ipfs_running() -> bool:
    """
    Check if the IPFS daemon is running

    Returns:
        Boolean indicating if the IPFS daemon is running
    """
    # First try the standard command
    result = run_ipfs_command(["id"])

    if result["success"]:
        print("IPFS daemon is running (verified with 'ipfs id')")
        return True

    # If that fails, try using the HTTP API directly
    try:
        import requests
        response = requests.post("http://localhost:5001/api/v0/id")
        if response.status_code == 200:
            print("IPFS daemon is running (verified with HTTP API)")
            return True
    except Exception as e:
        print(f"Error checking IPFS HTTP API: {str(e)}")

    print("IPFS daemon is not running or not accessible")
    return False

def verify_ipfs_content(cid: str) -> Dict:
    """
    Verify if a CID exists in IPFS

    Args:
        cid: The CID to verify

    Returns:
        Dict with keys:
            - exists: Boolean indicating if the CID exists
            - size: Size of the content in bytes (if exists)
            - error: Error message (if not exists)
            - daemon_running: Boolean indicating if the IPFS daemon is running
    """
    # First check if IPFS daemon is running
    daemon_running = is_ipfs_running()
    if not daemon_running:
        return {
            "exists": False,
            "daemon_running": False,
            "error": "IPFS daemon is not running or not accessible"
        }

    # Try using the HTTP API first (more reliable)
    try:
        # Try to get block stats using HTTP API
        api_result = use_ipfs_http_api(f"block/stat?arg={cid}", method="get")

        if api_result["success"]:
            # Get the size from the API response
            size = 0
            if isinstance(api_result["data"], dict) and "Size" in api_result["data"]:
                size = api_result["data"]["Size"]

            return {
                "exists": True,
                "daemon_running": True,
                "size": size,
                "method": "http_api_block_stat"
            }
    except Exception as api_error:
        print(f"Error using HTTP API for block/stat: {str(api_error)}")

    # If HTTP API fails, fall back to CLI commands
    try:
        # Try to get block stats
        result = run_ipfs_command(["block", "stat", cid])

        if result["success"]:
            # Parse the output to get the size
            size = 0
            for line in result["output"].splitlines():
                if line.startswith("Size:"):
                    try:
                        size = int(line.split("Size:")[1].strip())
                    except:
                        pass

            return {
                "exists": True,
                "daemon_running": True,
                "size": size,
                "method": "cli_block_stat"
            }
        else:
            # Try to get object stats as fallback
            obj_result = run_ipfs_command(["object", "stat", cid])

            if obj_result["success"]:
                # Parse the output to get the size
                size = 0
                for line in obj_result["output"].splitlines():
                    if line.startswith("DataSize:"):
                        try:
                            size = int(line.split("DataSize:")[1].strip())
                        except:
                            pass

                return {
                    "exists": True,
                    "daemon_running": True,
                    "size": size,
                    "method": "cli_object_stat"
                }
            else:
                # Try one more approach - cat with head to see if content exists
                try:
                    # Try HTTP API cat
                    cat_api_result = use_ipfs_http_api(f"cat?arg={cid}&length=1", method="get")
                    if cat_api_result["success"]:
                        return {
                            "exists": True,
                            "daemon_running": True,
                            "size": 1,  # We only know it's at least 1 byte
                            "method": "http_api_cat"
                        }
                except Exception as cat_api_error:
                    print(f"Error using HTTP API for cat: {str(cat_api_error)}")

                # Try CLI cat as last resort
                cat_result = run_ipfs_command(["cat", "--length=1", cid])
                if cat_result["success"]:
                    return {
                        "exists": True,
                        "daemon_running": True,
                        "size": 1,  # We only know it's at least 1 byte
                        "method": "cli_cat"
                    }
                else:
                    # All methods failed, the content probably doesn't exist
                    return {
                        "exists": False,
                        "daemon_running": True,
                        "error": result["error"]
                    }
    except Exception as e:
        return {
            "exists": False,
            "daemon_running": True,
            "error": str(e)
        }

def get_ipfs_version() -> str:
    """
    Get the IPFS daemon version

    Returns:
        String with the IPFS daemon version
    """
    result = run_ipfs_command(["version"])

    if result["success"]:
        return result["output"].strip()
    else:
        return "Unknown"

def use_ipfs_http_api(endpoint: str, method: str = "post", files=None, params=None) -> Dict:
    """
    Use the IPFS HTTP API directly

    Args:
        endpoint: The API endpoint (without the /api/v0/ prefix)
        method: The HTTP method to use (get or post)
        files: Files to upload (for post requests)
        params: Query parameters

    Returns:
        Dict with the API response or error
    """
    try:
        import requests

        # Build the URL
        base_url = "http://localhost:5001/api/v0"
        url = f"{base_url}/{endpoint}"

        print(f"Calling IPFS HTTP API: {url}")

        # Make the request
        if method.lower() == "get":
            response = requests.get(url, params=params)
        else:
            response = requests.post(url, files=files, params=params)

        # Check if the request was successful
        if response.status_code == 200:
            try:
                # Try to parse as JSON
                return {
                    "success": True,
                    "data": response.json()
                }
            except:
                # Return raw content if not JSON
                return {
                    "success": True,
                    "data": response.content
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
