#!/usr/bin/env python3
import os
import sys
import ipfshttpclient
import json
import hashlib
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ipfs_connection(ipfs_url=None):
    """Test connection to IPFS"""
    # Try multiple IPFS URLs if none is provided
    if ipfs_url is None:
        ipfs_urls = [
            os.getenv("IPFS_URL", "/ip4/127.0.0.1/tcp/5001"),
            "/ip4/127.0.0.1/tcp/5001",
            "/ip4/localhost/tcp/5001"
        ]
    else:
        ipfs_urls = [ipfs_url]

    # Try each URL
    for url in ipfs_urls:
        try:
            print(f"Trying to connect to IPFS at {url}...")
            client = ipfshttpclient.connect(url)

            # Get IPFS node info
            node_id = client.id()
            print(f"✅ Connected to IPFS node {node_id['ID']}")
            print(f"  Protocol version: {node_id['ProtocolVersion']}")
            print(f"  Agent version: {node_id['AgentVersion']}")

            return client
        except Exception as e:
            print(f"❌ Failed to connect to IPFS at {url}: {e}")

    print("❌ Could not connect to any IPFS node")
    return None

def test_ipfs_operations(client):
    """Test basic IPFS operations"""
    if client is None:
        print("❌ No IPFS client available")
        return False

    try:
        # Create test data
        test_data = {
            "timestamp": int(time.time()),
            "message": "Hello from Healthcare Data Sharing!",
            "test_id": hashlib.sha256(str(time.time()).encode()).hexdigest()[:10]
        }

        # Convert to JSON
        test_json = json.dumps(test_data).encode()

        print("\nTesting IPFS operations...")

        # Add data to IPFS
        print("Adding data to IPFS...")
        res = client.add_bytes(test_json)
        test_cid = res
        print(f"✅ Added data to IPFS with CID: {test_cid}")

        # Pin the data
        print("Pinning data...")
        client.pin.add(test_cid)
        print(f"✅ Pinned data with CID: {test_cid}")

        # Retrieve the data
        print("Retrieving data...")
        retrieved_data = client.cat(test_cid)
        retrieved_json = json.loads(retrieved_data)
        print(f"✅ Retrieved data: {json.dumps(retrieved_json, indent=2)}")

        # Verify the data
        if retrieved_json == test_data:
            print("✅ Data verification successful!")
        else:
            print("❌ Data verification failed!")
            return False

        # List pins
        print("\nListing pins...")
        pins = client.pin.ls()
        print(f"✅ Found {len(pins['Keys'])} pinned items")

        # Check if our test CID is pinned
        if test_cid in pins["Keys"]:
            print(f"✅ Test CID {test_cid} is pinned")
        else:
            print(f"❌ Test CID {test_cid} is not pinned")

        # Unpin the data (optional)
        print("\nUnpinning test data...")
        client.pin.rm(test_cid)
        print(f"✅ Unpinned data with CID: {test_cid}")

        return True
    except Exception as e:
        print(f"❌ Error during IPFS operations: {e}")
        return False

def main():
    """Main function"""
    print("Testing IPFS connection and operations...")

    # Test connection
    client = test_ipfs_connection()
    if client is None:
        return 1

    # Test operations
    if not test_ipfs_operations(client):
        return 1

    print("\n✅ All IPFS tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
