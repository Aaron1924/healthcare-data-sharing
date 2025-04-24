import os
import requests
import datetime

# Basescan API key
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "I61T8UZK7YKRC8P61BHF6237PG9GC2VK3Y")

# DataHub contract address on BASE Sepolia
DATAHUB_CONTRACT_ADDRESS = os.getenv("DATAHUB_CONTRACT_ADDRESS", "0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA")

# Function to fetch contract transactions from Basescan
def fetch_contract_transactions():
    """Fetch recent transactions for the DataHub contract from Basescan API
    
    Returns:
        list: Recent transactions involving the DataHub contract
    """
    try:
        # Get transactions to/from the contract
        contract_address = DATAHUB_CONTRACT_ADDRESS
        
        # Basescan API endpoint
        base_url = "https://api-sepolia.basescan.org/api"
        
        # Parameters for the API call
        params = {
            "module": "account",
            "action": "txlist",
            "address": contract_address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 10,  # Get the last 10 transactions
            "sort": "desc",  # Sort by newest first
            "apikey": BASESCAN_API_KEY
        }
        
        # Make the API call
        response = requests.get(base_url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if the API returned a success status
            if data.get("status") == "1" and "result" in data:
                raw_transactions = data["result"]
                transactions = []
                
                # Process each transaction
                for tx in raw_transactions:
                    # Get function name from input data if available
                    function_name = "Unknown"
                    if tx.get("input") and len(tx.get("input")) > 10:
                        # Extract function signature (first 10 characters after '0x')
                        function_sig = tx.get("input")[:10]
                        
                        # Map common function signatures to names
                        function_map = {
                            "0x": "ETH Transfer",
                            "0xa19c3b77": "storeData",
                            "0x59c87d70": "request",
                            "0xfc7c7931": "reply",
                            "0x6857ab40": "finalize",
                            "0x242dc0aa": "setRevocationManager",
                            "0xb328b69d": "setGroupManager",
                            "0x06d42882": "approveOpeningGroupManager",
                            "0x9d2fdac5": "approveOpeningRevocationManager",
                            "0xbb54cd6d": "requestOpening"
                        }
                        
                        function_name = function_map.get(function_sig, "Contract Interaction")
                    elif tx.get("input") == "0x":
                        function_name = "ETH Transfer"
                    
                    # Convert gas price from wei to gwei
                    gas_price_gwei = float(tx.get("gasPrice", "0")) / 1e9
                    
                    # Calculate gas fee in ETH
                    gas_used = int(tx.get("gasUsed", "0"))
                    gas_fee = (gas_used * gas_price_gwei * 1e-9)  # Convert to ETH
                    
                    # Create a standardized transaction object
                    transaction = {
                        "hash": tx.get("hash", ""),
                        "from": tx.get("from", ""),
                        "to": tx.get("to", ""),
                        "value": tx.get("value", "0"),
                        "function": function_name,
                        "timestamp": int(tx.get("timeStamp", "0")),
                        "gas_used": gas_used,
                        "gas_price": gas_price_gwei,  # Gwei
                        "status": "Success" if tx.get("txreceipt_status") == "1" else "Failed",
                        "gas_fee": gas_fee
                    }
                    
                    transactions.append(transaction)
                
                return transactions
            else:
                print(f"Basescan API error: {data.get('message', 'Unknown error')}")
                # Fall back to mock data if API fails
                return get_mock_transactions(contract_address)
        else:
            print(f"Failed to fetch data from Basescan API: {response.status_code}")
            # Fall back to mock data if API fails
            return get_mock_transactions(contract_address)
    except Exception as e:
        print(f"Error fetching contract transactions: {str(e)}")
        # Fall back to mock data if there's an exception
        return get_mock_transactions(DATAHUB_CONTRACT_ADDRESS)

# Function to provide mock transaction data as fallback
def get_mock_transactions(contract_address):
    """Generate mock transaction data for testing
    
    Args:
        contract_address: The contract address to use in the mock data
        
    Returns:
        list: Mock transaction data
    """
    print("Using mock transaction data as fallback")
    transactions = [
        {
            "hash": "0xc3df3885a00b773b549c3164f2984f943bab09d3ddfd28b65141a910efbbc566",
            "from": "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",
            "to": contract_address,
            "value": "0",
            "function": "Contract Creation",
            "timestamp": int(datetime.datetime.now().timestamp()) - 86400 * 7,  # 7 days ago
            "gas_used": 1500000,
            "gas_price": 0.1,  # Gwei
            "status": "Success",
            "gas_fee": 0.15  # ETH
        },
        {
            "hash": "0x8a7d2e13b0d2e8b65f9d5f38b6b1a67980c89d9c6c8b8a7e4f0a7f9c7e8d6b5a",
            "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            "to": contract_address,
            "value": "0",
            "function": "storeData",
            "timestamp": int(datetime.datetime.now().timestamp()) - 86400 * 3,  # 3 days ago
            "gas_used": 120000,
            "gas_price": 0.15,  # Gwei
            "status": "Success",
            "gas_fee": 0.018  # ETH
        },
        {
            "hash": "0x7b6c4e8d5f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6",
            "from": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",
            "to": contract_address,
            "value": "100000000000000000",  # 0.1 ETH
            "function": "request",
            "timestamp": int(datetime.datetime.now().timestamp()) - 86400 * 2,  # 2 days ago
            "gas_used": 80000,
            "gas_price": 0.12,  # Gwei
            "status": "Success",
            "gas_fee": 0.0096  # ETH
        },
        {
            "hash": "0x6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4",
            "from": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",
            "to": contract_address,
            "value": "0",
            "function": "reply",
            "timestamp": int(datetime.datetime.now().timestamp()) - 86400 * 1,  # 1 day ago
            "gas_used": 95000,
            "gas_price": 0.14,  # Gwei
            "status": "Success",
            "gas_fee": 0.0133  # ETH
        },
        {
            "hash": "0x5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3",
            "from": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",
            "to": contract_address,
            "value": "0",
            "function": "finalize",
            "timestamp": int(datetime.datetime.now().timestamp()) - 3600 * 12,  # 12 hours ago
            "gas_used": 110000,
            "gas_price": 0.13,  # Gwei
            "status": "Success",
            "gas_fee": 0.0143  # ETH
        }
    ]
    
    return transactions

# Function to fetch real-time gas prices from BASE Sepolia
def fetch_base_gas_prices():
    """Fetch current gas prices from BASE Sepolia network
    
    Returns:
        dict: Gas price information including base fee, priority fee estimates, and gas price in Gwei
    """
    try:
        # Basescan API endpoint for gas oracle
        base_url = "https://api-sepolia.basescan.org/api"
        
        # Parameters for the API call
        params = {
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": BASESCAN_API_KEY
        }
        
        # Make the API call
        response = requests.get(base_url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if the API returned a success status
            if data.get("status") == "1" and "result" in data:
                result = data["result"]
                
                # Extract gas prices
                safe_gas_price = float(result.get("SafeGasPrice", "0.1"))
                propose_gas_price = float(result.get("ProposeGasPrice", "0.5"))
                fast_gas_price = float(result.get("FastGasPrice", "1.0"))
                
                # Get the latest block to extract base fee
                base_fee_gwei = float(result.get("suggestBaseFee", "0.1"))
                
                # Get the latest block number
                latest_block = int(result.get("LastBlock", "0"))
                
                # Check contract deployment status
                contract_deployed = True  # Assume deployed for now
                
                return {
                    "network": "BASE Sepolia",
                    "block_number": latest_block,
                    "base_fee_gwei": round(base_fee_gwei, 2),
                    "gas_price_gwei": round(propose_gas_price, 2),
                    "slow": {
                        "priority_fee_gwei": 0.1,
                        "total_gwei": round(safe_gas_price, 2),
                        "estimated_cost": {
                            "simple_transfer": round(21000 * safe_gas_price * 1e-9, 6),  # ETH cost for simple transfer
                            "contract_interaction": round(100000 * safe_gas_price * 1e-9, 6)  # ETH cost for contract interaction
                        }
                    },
                    "average": {
                        "priority_fee_gwei": 0.5,
                        "total_gwei": round(propose_gas_price, 2),
                        "estimated_cost": {
                            "simple_transfer": round(21000 * propose_gas_price * 1e-9, 6),
                            "contract_interaction": round(100000 * propose_gas_price * 1e-9, 6)
                        }
                    },
                    "fast": {
                        "priority_fee_gwei": 1.0,
                        "total_gwei": round(fast_gas_price, 2),
                        "estimated_cost": {
                            "simple_transfer": round(21000 * fast_gas_price * 1e-9, 6),
                            "contract_interaction": round(100000 * fast_gas_price * 1e-9, 6)
                        }
                    },
                    "contract_status": {
                        "address": DATAHUB_CONTRACT_ADDRESS,
                        "deployed": contract_deployed
                    },
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                print(f"Basescan API error: {data.get('message', 'Unknown error')}")
                # Return fallback values if API fails
                return get_fallback_gas_prices()
        else:
            print(f"Failed to fetch data from Basescan API: {response.status_code}")
            # Return fallback values if API fails
            return get_fallback_gas_prices()
    except Exception as e:
        print(f"Error fetching gas prices: {str(e)}")
        # Return fallback values if there's an exception
        return get_fallback_gas_prices()

# Function to provide fallback gas price data
def get_fallback_gas_prices():
    """Generate fallback gas price data when API fails
    
    Returns:
        dict: Fallback gas price information
    """
    print("Using fallback gas price data")
    return {
        "network": "BASE Sepolia",
        "block_number": 0,
        "base_fee_gwei": 0.1,
        "gas_price_gwei": 0.5,
        "slow": {
            "priority_fee_gwei": 0.1,
            "total_gwei": 0.2,
            "estimated_cost": {
                "simple_transfer": 0.000004,
                "contract_interaction": 0.00002
            }
        },
        "average": {
            "priority_fee_gwei": 0.5,
            "total_gwei": 0.6,
            "estimated_cost": {
                "simple_transfer": 0.000012,
                "contract_interaction": 0.00006
            }
        },
        "fast": {
            "priority_fee_gwei": 1.0,
            "total_gwei": 1.1,
            "estimated_cost": {
                "simple_transfer": 0.000022,
                "contract_interaction": 0.00011
            }
        },
        "contract_status": {
            "address": DATAHUB_CONTRACT_ADDRESS,
            "deployed": True
        },
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# Test the functions if run directly
if __name__ == "__main__":
    # Test fetching gas prices
    gas_prices = fetch_base_gas_prices()
    print("Gas Prices:")
    print(f"Base Fee: {gas_prices['base_fee_gwei']} Gwei")
    print(f"Gas Price: {gas_prices['gas_price_gwei']} Gwei")
    print(f"Slow: {gas_prices['slow']['total_gwei']} Gwei")
    print(f"Average: {gas_prices['average']['total_gwei']} Gwei")
    print(f"Fast: {gas_prices['fast']['total_gwei']} Gwei")
    
    # Test fetching transactions
    transactions = fetch_contract_transactions()
    print(f"\nFound {len(transactions)} transactions")
    for i, tx in enumerate(transactions[:3]):  # Show first 3 transactions
        print(f"\nTransaction {i+1}:")
        print(f"Hash: {tx['hash']}")
        print(f"From: {tx['from']}")
        print(f"Function: {tx['function']}")
        print(f"Gas Used: {tx['gas_used']}")
        print(f"Gas Fee: {tx['gas_fee']} ETH")
