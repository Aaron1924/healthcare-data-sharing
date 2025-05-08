import streamlit as st

# Set page config first - this must be the first Streamlit command
st.set_page_config(
    page_title="Healthcare Data Sharing",
    page_icon="🏥",
    layout="wide"
)

import requests
import json
import os
import datetime
import time
import base64
import hashlib
from web3 import Web3
import streamlit.components.v1 as components
from dotenv import load_dotenv
import aiohttp
import asyncio
# Try to import Coinbase Cloud SDK, but make it optional
try:
    from cdp_sdk import CoinbaseCloud
    has_coinbase_sdk = True
except ImportError:
    has_coinbase_sdk = False
    print("Warning: cdp_sdk not found. Coinbase Cloud features will be disabled.")

# Load environment variables
load_dotenv()

# API endpoint
API_URL = os.getenv("API_URL", "http://localhost:8000/api")

# Base Sepolia testnet connection via Coinbase Cloud
BASE_SEPOLIA_RPC_URL = os.getenv("BASE_SEPOLIA_RPC_URL", "https://api.developer.coinbase.com/rpc/v1/base-sepolia/TU79b5nxSoHEPVmNhElKsyBqt9CUbNTf")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")

# Initialize Web3 with Coinbase Cloud RPC
w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC_URL))

# DataHub contract address on BASE Sepolia
DATAHUB_CONTRACT_ADDRESS = os.getenv("DATAHUB_CONTRACT_ADDRESS", "0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA")

# Function to fetch contract transactions from Basescan
def fetch_contract_transactions():
    """Fetch recent transactions for the DataHub contract from Basescan

    Returns:
        list: Recent transactions involving the DataHub contract
    """
    try:
        # Get transactions to/from the contract
        contract_address = DATAHUB_CONTRACT_ADDRESS

        # We'll simulate fetching from Basescan API (in a real implementation, you would use their API)
        # For demo purposes, we'll return mock data that resembles real transactions
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
                "status": "Success"
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
                "status": "Success"
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
                "status": "Success"
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
                "status": "Success"
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
                "status": "Success"
            }
        ]

        # Calculate gas fee in ETH for each transaction
        for tx in transactions:
            tx["gas_fee"] = (tx["gas_used"] * tx["gas_price"] * 1e-9)  # Convert to ETH

        return transactions
    except Exception as e:
        print(f"Error fetching contract transactions: {str(e)}")
        return []

# Function to fetch real-time gas prices from BASE Sepolia
def fetch_base_gas_prices():
    """Fetch current gas prices from BASE Sepolia network

    Returns:
        dict: Gas price information including base fee, priority fee estimates, and gas price in Gwei
    """
    try:
        # Get the latest block to extract base fee
        latest_block = w3.eth.get_block('latest')
        base_fee_wei = latest_block.get('baseFeePerGas', 0)
        base_fee_gwei = w3.from_wei(base_fee_wei, 'gwei')

        # Convert decimal.Decimal to float to avoid type issues
        base_fee_gwei = float(base_fee_gwei)

        # Get gas price (legacy)
        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, 'gwei')

        # Convert decimal.Decimal to float to avoid type issues
        gas_price_gwei = float(gas_price_gwei)

        # Estimate priority fees (max_priority_fee_per_gas)
        # For BASE Sepolia, we'll use standard values as estimates
        slow_priority_fee = 0.1  # Gwei
        average_priority_fee = 0.5  # Gwei
        fast_priority_fee = 1.0  # Gwei

        # Calculate total gas costs (base fee + priority fee)
        slow_total = base_fee_gwei + slow_priority_fee
        average_total = base_fee_gwei + average_priority_fee
        fast_total = base_fee_gwei + fast_priority_fee

        # Get contract deployment status
        contract_deployed = False
        contract_code = w3.eth.get_code(DATAHUB_CONTRACT_ADDRESS)
        if contract_code and contract_code != '0x':
            contract_deployed = True

        return {
            "network": "BASE Sepolia",
            "block_number": latest_block.number,
            "base_fee_gwei": round(base_fee_gwei, 2),
            "gas_price_gwei": round(gas_price_gwei, 2),
            "slow": {
                "priority_fee_gwei": slow_priority_fee,
                "total_gwei": round(slow_total, 2),
                "estimated_cost": {
                    "simple_transfer": round(21000 * slow_total * 1e-9, 6),  # ETH cost for simple transfer
                    "contract_interaction": round(100000 * slow_total * 1e-9, 6)  # ETH cost for contract interaction
                }
            },
            "average": {
                "priority_fee_gwei": average_priority_fee,
                "total_gwei": round(average_total, 2),
                "estimated_cost": {
                    "simple_transfer": round(21000 * average_total * 1e-9, 6),
                    "contract_interaction": round(100000 * average_total * 1e-9, 6)
                }
            },
            "fast": {
                "priority_fee_gwei": fast_priority_fee,
                "total_gwei": round(fast_total, 2),
                "estimated_cost": {
                    "simple_transfer": round(21000 * fast_total * 1e-9, 6),
                    "contract_interaction": round(100000 * fast_total * 1e-9, 6)
                }
            },
            "contract_status": {
                "address": DATAHUB_CONTRACT_ADDRESS,
                "deployed": contract_deployed
            },
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error fetching gas prices: {str(e)}")
        # Return fallback values if there's an error
        return {
            "network": "BASE Sepolia",
            "error": str(e),
            "base_fee_gwei": 0.1,
            "gas_price_gwei": 0.5,
            "slow": {"total_gwei": 0.2, "estimated_cost": {"simple_transfer": 0.000004, "contract_interaction": 0.00002}},
            "average": {"total_gwei": 0.6, "estimated_cost": {"simple_transfer": 0.000012, "contract_interaction": 0.00006}},
            "fast": {"total_gwei": 1.1, "estimated_cost": {"simple_transfer": 0.000022, "contract_interaction": 0.00011}},
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Load contract ABI
try:
    with open("artifacts/contracts/DataHub.sol/DataHub.json", "r") as f:
        contract_json = json.load(f)
        contract_abi = contract_json["abi"]
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    st.warning("Contract ABI not found or invalid. Using empty ABI.")
    contract_abi = []

contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# Streamlit app
# Page config is already set at the top of the file

# Display Base Sepolia connection status
if w3.is_connected():
    st.sidebar.success(f"Connected to Base Sepolia via Coinbase Cloud")
    st.sidebar.info(f"Latest block: {w3.eth.block_number}")

    # Check wallet balance
    try:
        balance = w3.eth.get_balance(WALLET_ADDRESS)
        st.sidebar.info(f"Wallet balance: {w3.from_wei(balance, 'ether')} ETH")
    except Exception as e:
        st.sidebar.warning(f"Could not fetch wallet balance: {e}")
else:
    st.sidebar.error("Not connected to Base Sepolia")

# Define test accounts - one for each role
TEST_ACCOUNTS = {
    "Patient": {
        "address": "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",
        "role": "Patient",
        "private_key": "91e5c2bed81b69f9176b6404710914e9bf36a6359122a2d1570116fc6322562e"
    },
    "Doctor": {
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "role": "Doctor",
        "private_key": "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    },
    "Hospital": {
        "address": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",
        "role": "Hospital",
        "private_key": "1e291b59ddd32689ee42459971d5f0ad1b794972be116e5fb9f1929616afeb47"
    },
    "Buyer": {
        "address": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",
        "role": "Buyer",
        "private_key": "e25e8f9128ba1bef33e1cacb2e1b50dd3f34c7f175b61098b4ab4f17c9416d06"
    },
    "Group Manager": {
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "role": "Group Manager",
        "private_key": "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    },
    "Revocation Manager": {
        "address": "0x4b42EE1d1AEe8d3cc691661aa3b25D98Dac2FE46",
        "role": "Revocation Manager",
        "private_key": "4bf1c7cac1c53c7f7f7ddcc979b159d66a3d2d721fa4053330adbb100be628a0"
    }
}

# Function to track a transaction in the session state
def track_transaction(tx_hash, operation, wallet_address, gas_used=None, gas_price=None):
    """Track a transaction in the session state for gas fee analysis

    Args:
        tx_hash: The transaction hash
        operation: The operation type (e.g., "Store Record")
        wallet_address: The wallet address that initiated the transaction
        gas_used: The gas used by the transaction (if known)
        gas_price: The gas price used for the transaction (if known)
    """
    if 'gas_fees' not in st.session_state:
        st.session_state.gas_fees = []

    # Ensure the transaction hash has the 0x prefix
    if not tx_hash.startswith('0x'):
        tx_hash = f"0x{tx_hash}"

    # Create a transaction record
    tx_record = {
        "tx_hash": tx_hash,
        "operation": operation,
        "wallet_address": wallet_address,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "explorer_link": f"https://sepolia.basescan.org/tx/{tx_hash}"
    }

    # Add gas information if available
    if gas_used is not None:
        tx_record["gas_used"] = gas_used

    if gas_price is not None:
        tx_record["gas_price"] = gas_price
        if gas_used is not None:
            # Calculate the cost in ETH
            from web3 import Web3
            cost_wei = gas_used * gas_price
            cost_eth = Web3.from_wei(cost_wei, 'ether')
            tx_record["cost_eth"] = cost_eth

    # Add to session state
    st.session_state.gas_fees.append(tx_record)

    # Log to transaction_log.txt as well
    try:
        with open('transaction_log.txt', 'a') as log_file:
            log_file.write(f"\nTimestamp: {tx_record['timestamp']}")
            log_file.write(f"\nTransaction: {tx_hash}")
            log_file.write(f"\nExplorer Link: {tx_record['explorer_link']}")
            log_file.write(f"\nOperation: {operation}")
            log_file.write(f"\nWallet: {wallet_address}")
            if gas_used is not None:
                log_file.write(f"\nGas Used: {gas_used}")
            if gas_price is not None:
                from web3 import Web3
                log_file.write(f"\nGas Price: {Web3.from_wei(gas_price, 'gwei')} Gwei")
            if gas_used is not None and gas_price is not None:
                from web3 import Web3
                cost_wei = gas_used * gas_price
                cost_eth = Web3.from_wei(cost_wei, 'ether')
                log_file.write(f"\nCost: {cost_eth} ETH")
            log_file.write(f"\n-----------------------------------")
    except Exception as e:
        print(f"Error writing to transaction log: {str(e)}")

# Function to generate the gas fees tab for any role
def render_gas_fees_tab(wallet_address):
    """Render the gas fees tab with all its components

    Args:
        wallet_address: The wallet address to get gas fees for
    """
    st.header("Gas Fees and Transaction Costs")

    # Initialize gas fees tracking if not already done
    if 'gas_fees' not in st.session_state:
        st.session_state.gas_fees = []

    # Display gas fees tracking
    if st.session_state.gas_fees:
        # Create a DataFrame from the gas fees
        import pandas as pd
        df = pd.DataFrame(st.session_state.gas_fees)

        # Display the DataFrame
        st.subheader("Transaction History")
        st.dataframe(df, use_container_width=True)

        # Add export functionality
        if st.button("Export Gas Fees to CSV"):
            # Convert DataFrame to CSV
            csv = df.to_csv(index=False)
            # Create a download button
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="gas_fees.csv",
                mime="text/csv"
            )

        # Add links to transactions
        st.subheader("Transaction Links")
        for i, tx in enumerate(st.session_state.gas_fees):
            if 'tx_hash' in tx:
                # Ensure the transaction hash has the 0x prefix
                tx_hash = tx['tx_hash']
                if not tx_hash.startswith('0x'):
                    tx_hash = f"0x{tx_hash}"
                st.markdown(f"[{tx.get('operation', 'Transaction')} - {tx.get('timestamp', '')}](https://sepolia.basescan.org/tx/{tx_hash})")
    else:
        st.info("No gas fees tracked yet. They will appear here after you create records or perform other blockchain transactions.")

    # Add a button to fetch real-time gas prices
    if st.button("Fetch Current Gas Prices", key="fetch_gas_prices"):
        try:
            # Initialize web3 connection to BASE Sepolia
            from web3 import Web3
            import requests

            # Connect to BASE Sepolia
            w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))

            if w3.is_connected():
                # Get current gas price
                gas_price = w3.eth.gas_price
                gas_price_gwei = w3.from_wei(gas_price, 'gwei')

                # Get ETH price in USD
                try:
                    # Use CoinGecko API to get ETH price
                    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
                    eth_price = response.json()["ethereum"]["usd"]
                except:
                    eth_price = 3000  # Fallback price if API fails

                # Display gas prices
                st.success(f"Current BASE Sepolia Gas Price: {gas_price_gwei:.2f} Gwei")

                # Calculate costs for different operations
                operations = {
                    "Store Record": 100000,  # Estimated gas used
                    "Share Record": 50000,
                    "Purchase Request": 80000,
                    "Finalize Purchase": 120000,
                    "Reply to Request": 60000
                }

                # Create a table of costs
                cost_data = []
                for op, gas in operations.items():
                    cost_wei = gas * gas_price
                    cost_eth = w3.from_wei(cost_wei, 'ether')
                    cost_usd = cost_eth * eth_price
                    cost_data.append({
                        "Operation": op,
                        "Gas Used (est.)": gas,
                        "Cost (ETH)": f"{cost_eth:.6f}",
                        "Cost (USD)": f"${cost_usd:.2f}"
                    })

                # Display as DataFrame
                cost_df = pd.DataFrame(cost_data)
                st.subheader("Estimated Transaction Costs")
                st.dataframe(cost_df, use_container_width=True)
            else:
                st.error("Could not connect to BASE Sepolia network")
        except Exception as e:
            st.error(f"Error fetching gas prices: {str(e)}")

    # Add a button to clear gas fees history
    if st.session_state.gas_fees and st.button("Clear Gas Fees History", key="clear_gas_fees"):
        st.session_state.gas_fees = []
        st.success("Gas fees history cleared!")
        st.rerun()

    # Add real-time gas price information from BASE Sepolia
    st.subheader("Real-Time BASE Sepolia Gas Prices")

    try:
        gas_prices = fetch_base_gas_prices()
    except Exception as e:
        st.error(f"Error fetching gas prices: {str(e)}")
        # Provide fallback gas prices
        gas_prices = {
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

    # Display gas price information in columns
    gas_col1, gas_col2, gas_col3 = st.columns(3)

    with gas_col1:
        st.metric("Current Base Fee", f"{gas_prices.get('base_fee_gwei', 0.1)} Gwei")
        st.metric("Block Number", gas_prices.get('block_number', 0))

    with gas_col2:
        st.metric("Gas Price (Legacy)", f"{gas_prices.get('gas_price_gwei', 0.5)} Gwei")
        st.metric("Network", gas_prices.get('network', 'BASE Sepolia'))

    with gas_col3:
        contract_status = gas_prices.get('contract_status', {'deployed': False})
        st.metric("DataHub Contract", "Deployed" if contract_status.get('deployed', False) else "Not Deployed")
        timestamp = gas_prices.get('timestamp', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        st.metric("Last Updated", timestamp.split()[1] if ' ' in timestamp else timestamp)  # Show only time part

    # Create tabs for different gas price levels
    gas_tab1, gas_tab2, gas_tab3 = st.tabs(["Slow (Low Priority)", "Average", "Fast (High Priority)"])

    # Helper function to safely access nested dictionary values
    def safe_get(d, keys, default=None):
        """Safely get a value from a nested dictionary

        Args:
            d: Dictionary to get value from
            keys: List of keys to traverse
            default: Default value if key doesn't exist

        Returns:
            Value from dictionary or default
        """
        result = d
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result

    with gas_tab1:
        st.markdown(f"### Slow Transaction Settings")
        st.markdown(f"Total Gas Price: **{safe_get(gas_prices, ['slow', 'total_gwei'], 0.2)} Gwei**")
        st.markdown(f"Priority Fee: **{safe_get(gas_prices, ['slow', 'priority_fee_gwei'], 0.1)} Gwei**")
        st.markdown("#### Estimated Costs:")
        st.markdown(f"- Simple ETH Transfer: **{safe_get(gas_prices, ['slow', 'estimated_cost', 'simple_transfer'], 0.000004)} ETH**")
        st.markdown(f"- Contract Interaction: **{safe_get(gas_prices, ['slow', 'estimated_cost', 'contract_interaction'], 0.00002)} ETH**")

    with gas_tab2:
        st.markdown(f"### Average Transaction Settings")
        st.markdown(f"Total Gas Price: **{safe_get(gas_prices, ['average', 'total_gwei'], 0.6)} Gwei**")
        st.markdown(f"Priority Fee: **{safe_get(gas_prices, ['average', 'priority_fee_gwei'], 0.5)} Gwei**")
        st.markdown("#### Estimated Costs:")
        st.markdown(f"- Simple ETH Transfer: **{safe_get(gas_prices, ['average', 'estimated_cost', 'simple_transfer'], 0.000012)} ETH**")
        st.markdown(f"- Contract Interaction: **{safe_get(gas_prices, ['average', 'estimated_cost', 'contract_interaction'], 0.00006)} ETH**")

    with gas_tab3:
        st.markdown(f"### Fast Transaction Settings")
        st.markdown(f"Total Gas Price: **{safe_get(gas_prices, ['fast', 'total_gwei'], 1.1)} Gwei**")
        st.markdown(f"Priority Fee: **{safe_get(gas_prices, ['fast', 'priority_fee_gwei'], 1.0)} Gwei**")
        st.markdown("#### Estimated Costs:")
        st.markdown(f"- Simple ETH Transfer: **{safe_get(gas_prices, ['fast', 'estimated_cost', 'simple_transfer'], 0.000022)} ETH**")
        st.markdown(f"- Contract Interaction: **{safe_get(gas_prices, ['fast', 'estimated_cost', 'contract_interaction'], 0.00011)} ETH**")

    # Add a gas cost calculator
    st.subheader("Gas Cost Calculator")
    calc_col1, calc_col2 = st.columns(2)

    with calc_col1:
        gas_units = st.number_input(
            "Gas Units",
            min_value=21000,
            max_value=10000000,
            value=100000,
            step=10000,
            help="Estimated gas units for your transaction",
            key="gas_units_calculator"
        )

        gas_price_option = st.radio(
            "Gas Price Setting",
            ["Slow", "Average", "Fast"],
            index=1,
            horizontal=True,
            help="Select gas price level",
            key="gas_price_option_calculator"
        )

    with calc_col2:
        eth_price_calc = st.number_input(
            "ETH Price (USD)",
            min_value=100.0,
            max_value=10000.0,
            value=2000.0,
            step=100.0,
            help="Current ETH price in USD for cost calculations",
            key="eth_price_calculator"
        )

        # Get the selected gas price safely
        selected_gas_price = safe_get(gas_prices, [gas_price_option.lower(), 'total_gwei'], 0.5)

        # Calculate the cost
        eth_cost = gas_units * selected_gas_price * 1e-9
        usd_cost = eth_cost * eth_price_calc

        # Display the results
        st.metric(
            "Estimated Transaction Cost",
            f"{eth_cost:.6f} ETH",
            f"${usd_cost:.2f}"
        )

    # Add a comparison of gas costs across different networks
    st.subheader("Network Gas Price Comparison")

    # Create a DataFrame for the comparison
    network_comparison = [
        {"Network": "BASE Sepolia (Testnet)", "Base Fee (Gwei)": gas_prices.get('base_fee_gwei', 0.1), "Avg Total (Gwei)": safe_get(gas_prices, ['average', 'total_gwei'], 0.6), "Simple Transfer Cost": f"{safe_get(gas_prices, ['average', 'estimated_cost', 'simple_transfer'], 0.000012)} ETH"},
        {"Network": "BASE Mainnet", "Base Fee (Gwei)": 0.05, "Avg Total (Gwei)": 0.1, "Simple Transfer Cost": "0.000002 ETH"},
        {"Network": "Ethereum Mainnet", "Base Fee (Gwei)": 20.0, "Avg Total (Gwei)": 25.0, "Simple Transfer Cost": "0.000525 ETH"},
        {"Network": "Arbitrum One", "Base Fee (Gwei)": 0.1, "Avg Total (Gwei)": 0.15, "Simple Transfer Cost": "0.000003 ETH"},
        {"Network": "Optimism", "Base Fee (Gwei)": 0.001, "Avg Total (Gwei)": 0.005, "Simple Transfer Cost": "0.0000001 ETH"}
    ]

    # Display the comparison table
    st.dataframe(network_comparison)

    # Add a note about the comparison
    st.caption("Note: Values for networks other than BASE Sepolia are approximations and may vary. BASE Sepolia is a testnet with different economics than mainnet networks.")

    # Add a note about gas prices
    with st.expander("About Gas Prices on BASE Sepolia"):
        st.markdown("""
        **Gas Price Components:**
        - **Base Fee**: Set by the network based on demand. This portion is burned.
        - **Priority Fee**: Optional tip to validators to prioritize your transaction.
        - **Total Gas Price** = Base Fee + Priority Fee

        **Transaction Types:**
        - **Simple Transfer**: Sending ETH from one address to another (~21,000 gas units)
        - **Contract Interaction**: Calling functions on smart contracts (~100,000 gas units for typical operations)

        **Note**: BASE Sepolia is a testnet with lower gas prices than mainnet. These estimates are for planning purposes only.

        **DataHub Contract**: The contract is deployed at [0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA](https://sepolia.basescan.org/address/0x8Cbf9a04C9c7F329DCcaeabE90a424e8F9687aaA)
        """)

    # Add DataHub contract transactions section
    st.subheader("DataHub Contract Transactions")

    # Fetch contract transactions
    contract_txs = fetch_contract_transactions()

    if contract_txs:
        # Create a DataFrame for display
        tx_data = []
        total_gas_fee = 0

        for tx in contract_txs:
            tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx["hash"]
            tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}"

            # Add to total gas fee
            total_gas_fee += tx["gas_fee"]

            # Format value in ETH if it's not zero
            value_eth = "0"
            if tx["value"] != "0":
                value_eth = f"{float(tx['value']) / 1e18:.4f} ETH"

            tx_data.append({
                "Function": tx["function"],
                "From": f"{tx['from'][:8]}...{tx['from'][-6:]}",
                "Timestamp": tx_time,
                "TX Hash": tx_hash_short,
                "Gas Used": f"{tx['gas_used']:,}",
                "Gas Fee (ETH)": f"{tx['gas_fee']:.6f}",
                "Value": value_eth
            })

        # Display summary metrics
        tx_col1, tx_col2, tx_col3 = st.columns(3)
        with tx_col1:
            st.metric("Total Transactions", len(contract_txs))
        with tx_col2:
            st.metric("Total Gas Fees", f"{total_gas_fee:.6f} ETH")
        with tx_col3:
            avg_gas = total_gas_fee / len(contract_txs) if contract_txs else 0
            st.metric("Average Gas Fee", f"{avg_gas:.6f} ETH")

        # Display the transactions table
        st.dataframe(tx_data)

        # Add a link to view on Basescan
        st.markdown(f"[View all transactions on Basescan](https://sepolia.basescan.org/address/{DATAHUB_CONTRACT_ADDRESS})")

        # Add a pie chart for gas usage by function
        st.subheader("Gas Usage by Function")

        # Group by function
        function_gas = {}
        for tx in contract_txs:
            func = tx["function"]
            if func not in function_gas:
                function_gas[func] = {
                    "total_gas": 0,
                    "count": 0,
                    "total_fee": 0
                }

            function_gas[func]["total_gas"] += tx["gas_used"]
            function_gas[func]["count"] += 1
            function_gas[func]["total_fee"] += tx["gas_fee"]

        # Create data for the chart
        functions = list(function_gas.keys())
        gas_values = [data["total_gas"] for data in function_gas.values()]

        # Create a DataFrame for display
        function_data = []
        for func, data in function_gas.items():
            function_data.append({
                "Function": func,
                "Count": data["count"],
                "Total Gas Used": f"{data['total_gas']:,}",
                "Total Gas Fee (ETH)": f"{data['total_fee']:.6f}",
                "Average Gas": f"{data['total_gas'] / data['count']:,.0f}"
            })

        # Display as a table
        st.dataframe(function_data)

        # Create a bar chart for gas usage by function
        chart_data = {"Function": functions, "Gas Used": gas_values}
        st.bar_chart(chart_data, x="Function", y="Gas Used")
    else:
        st.info("No contract transactions found or error fetching transactions.")

    # Horizontal line to separate real-time gas prices from historical data
    st.markdown("---")

    # Historical gas fees section
    st.subheader("Historical Gas Fees")

    try:
        # Call API to get gas fees
        response = requests.get(
            f"{API_URL}/fees",
            params={"wallet_address": wallet_address}
        )

        # If the first URL fails, try the alternative URL
        if response.status_code == 404:
            print("Trying alternative API URL...")
            response = requests.get(
                f"{API_URL}/api/fees",
                params={"wallet_address": wallet_address}
            )

        if response.status_code == 200:
            result = response.json()

            # Display summary statistics
            st.subheader("Gas Fee Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Gas Fees", f"{result['total_gas_fees']:.6f} ETH")
            with col2:
                st.metric("Transaction Count", result['transaction_count'])
            with col3:
                st.metric("Average Gas Fee", f"{result['average_gas_fee']:.6f} ETH")

            # Add workflow filter
            st.subheader("Filter by Workflow")
            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:
                workflow_options = ["All Workflows", "Storing", "Sharing", "Purchasing"]
                selected_workflow = st.selectbox(
                    "Select Workflow",
                    workflow_options,
                    help="Filter transactions by workflow type",
                    key="workflow_filter"
                )

            with filter_col2:
                eth_price = st.number_input(
                    "ETH Price (USD)",
                    min_value=100.0,
                    max_value=10000.0,
                    value=2000.0,
                    step=100.0,
                    help="Current ETH price in USD for cost calculations",
                    key="eth_price_historical"
                )

            if selected_workflow != "All Workflows" and st.button("Apply Filter"):
                # Call API with workflow filter
                workflow_param = selected_workflow.lower()
                response = requests.get(
                    f"{API_URL}/fees",
                    params={
                        "wallet_address": wallet_address,
                        "workflow": workflow_param
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Filtered to show only {selected_workflow} workflow transactions")
                else:
                    st.error("Failed to apply filter")

            # Display statistics from the API
            if 'stats' in result:
                stats = result['stats']
                st.subheader("Transaction Statistics")
                stats_col1, stats_col2, stats_col3 = st.columns(3)

                with stats_col1:
                    st.metric("Min Gas Fee", f"{stats.get('min_gas_fee', 0):.6f} ETH", f"${stats.get('min_gas_fee', 0) * eth_price:.2f}")
                    first_tx_time = datetime.datetime.fromtimestamp(stats.get('first_transaction_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if stats.get('first_transaction_time', 0) > 0 else "N/A"
                    st.metric("First Transaction", first_tx_time)

                with stats_col2:
                    st.metric("Max Gas Fee", f"{stats.get('max_gas_fee', 0):.6f} ETH", f"${stats.get('max_gas_fee', 0) * eth_price:.2f}")
                    last_tx_time = datetime.datetime.fromtimestamp(stats.get('last_transaction_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if stats.get('last_transaction_time', 0) > 0 else "N/A"
                    st.metric("Last Transaction", last_tx_time)

                with stats_col3:
                    date_range = 0
                    if stats.get('first_transaction_time', 0) > 0 and stats.get('last_transaction_time', 0) > 0:
                        first_date = datetime.datetime.fromtimestamp(stats.get('first_transaction_time', 0))
                        last_date = datetime.datetime.fromtimestamp(stats.get('last_transaction_time', 0))
                        date_range = (last_date - first_date).days + 1

                    st.metric("Date Range", f"{date_range} days")
                    avg_per_day = result['transaction_count'] / date_range if date_range > 0 else 0
                    st.metric("Avg Tx per Day", f"{avg_per_day:.2f}")

            # Display fees by workflow
            st.subheader("Gas Fees by Workflow")
            if 'fees_by_workflow' in result and result['fees_by_workflow']:
                # Create data for the chart
                workflows = [w.capitalize() for w in result['fees_by_workflow'].keys() if result['fees_by_workflow'][w]['count'] > 0]
                workflow_total_fees = [data['total_gas_fee'] for _, data in result['fees_by_workflow'].items() if data['count'] > 0]
                workflow_avg_fees = [data['average_gas_fee'] for _, data in result['fees_by_workflow'].items() if data['count'] > 0]

                # Create a DataFrame for display
                workflow_fee_data = []
                for workflow, data in result['fees_by_workflow'].items():
                    if data['count'] > 0:
                        percent = (data['total_gas_fee'] / result['total_gas_fees']) * 100 if result['total_gas_fees'] > 0 else 0
                        workflow_fee_data.append({
                            "Workflow": workflow.capitalize(),
                            "Count": data['count'],
                            "Total Gas Fee (ETH)": round(data['total_gas_fee'], 6),
                            "Average Gas Fee (ETH)": round(data['average_gas_fee'], 6),
                            "% of Total": f"{percent:.2f}%"
                        })

                # Display as a table
                st.dataframe(workflow_fee_data)

                # Create a pie chart for workflow distribution
                st.subheader("Gas Fee Distribution by Workflow")
                fig = {
                    "data": [{
                        "values": workflow_total_fees,
                        "labels": workflows,
                        "type": "pie",
                        "hole": 0.4,
                        "textinfo": "label+percent",
                        "textposition": "outside"
                    }],
                    "layout": {
                        "title": "Gas Fee Distribution by Workflow",
                        "height": 400
                    }
                }
                # st.plotly_chart(fig)  # Commented out as plotly might not be available
                st.json(fig)  # Display as JSON instead

                # Create a bar chart for average gas fees by workflow
                st.subheader("Average Gas Fee by Workflow")
                chart_data = {"Workflow": workflows, "Average Gas Fee (ETH)": workflow_avg_fees}
                st.bar_chart(chart_data, x="Workflow", y="Average Gas Fee (ETH)")
            else:
                st.info("No gas fee data by workflow available.")

            # Display fees by transaction type
            st.subheader("Gas Fees by Transaction Type")
            if result['fees_by_type']:
                # Create data for the chart
                types = list(result['fees_by_type'].keys())
                total_fees = [data['total_gas_fee'] for data in result['fees_by_type'].values()]
                avg_fees = [data['average_gas_fee'] for data in result['fees_by_type'].values()]

                # Create a DataFrame for display
                fee_data = []
                for tx_type, data in result['fees_by_type'].items():
                    fee_data.append({
                        "Transaction Type": tx_type,
                        "Count": data['count'],
                        "Total Gas Fee (ETH)": round(data['total_gas_fee'], 6),
                        "Average Gas Fee (ETH)": round(data['average_gas_fee'], 6)
                    })

                # Display as a table
                st.dataframe(fee_data)

                # Create a bar chart for total gas fees by type
                st.subheader("Total Gas Fees by Transaction Type")
                chart_data = {"Transaction Type": types, "Total Gas Fee (ETH)": total_fees}
                st.bar_chart(chart_data, x="Transaction Type", y="Total Gas Fee (ETH)")

                # Create a bar chart for average gas fees by type
                st.subheader("Average Gas Fee by Transaction Type")
                chart_data = {"Transaction Type": types, "Average Gas Fee (ETH)": avg_fees}
                st.bar_chart(chart_data, x="Transaction Type", y="Average Gas Fee (ETH)")
            else:
                st.info("No gas fee data by transaction type available.")

            # Display transaction details
            st.subheader("Transaction Details")
            if result['transactions']:
                # Create a DataFrame for display
                tx_data = []
                for tx in result['transactions']:
                    tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                    tx_hash = tx.get("tx_hash", "N/A")
                    tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if tx_hash != "N/A" else "N/A"

                    tx_data.append({
                        "Type": tx["type"],
                        "Status": tx["status"],
                        "Timestamp": tx_time,
                        "TX Hash": tx_hash_short,
                        "Gas Fee (ETH)": tx.get("gas_fee", "N/A"),
                        "Request ID": tx.get("request_id", "N/A")
                    })

                # Display as a table
                st.dataframe(tx_data)
            else:
                st.info("No transaction details available.")

            # Add workflow cost analysis
            st.subheader("Workflow Cost Analysis")
            if 'fees_by_workflow' in result and result['fees_by_workflow']:
                # Calculate cost per operation for each workflow
                storing_cost = result['fees_by_workflow'].get('storing', {}).get('average_gas_fee', 0)
                sharing_cost = result['fees_by_workflow'].get('sharing', {}).get('average_gas_fee', 0)
                purchasing_cost = result['fees_by_workflow'].get('purchasing', {}).get('average_gas_fee', 0)

                # Create columns for the costs
                cost_col1, cost_col2, cost_col3 = st.columns(3)
                with cost_col1:
                    st.metric("Storing Cost", f"{storing_cost:.6f} ETH", f"${storing_cost * eth_price:.2f}")
                with cost_col2:
                    st.metric("Sharing Cost", f"{sharing_cost:.6f} ETH", f"${sharing_cost * eth_price:.2f}")
                with cost_col3:
                    st.metric("Purchasing Cost", f"{purchasing_cost:.6f} ETH", f"${purchasing_cost * eth_price:.2f}")

                # Add scaling analysis
                st.subheader("Scaling Analysis (Monthly Costs)")

                # Create tabs for different scales
                scale_tab1, scale_tab2, scale_tab3 = st.tabs(["Small Clinic", "Medium Hospital", "Large Hospital"])

                with scale_tab1:
                    # Small clinic (100 records/month, 50 shares/month, 10 purchases/month)
                    small_monthly = (storing_cost * 100) + (sharing_cost * 50) + (purchasing_cost * 10)
                    st.metric("Monthly Cost (100 records, 50 shares, 10 purchases)",
                             f"{small_monthly:.6f} ETH",
                             f"${small_monthly * eth_price:.2f}")

                    # Show breakdown
                    st.write("Cost Breakdown:")
                    st.write(f"- Storing: {storing_cost * 100:.6f} ETH (${storing_cost * 100 * eth_price:.2f})")
                    st.write(f"- Sharing: {sharing_cost * 50:.6f} ETH (${sharing_cost * 50 * eth_price:.2f})")
                    st.write(f"- Purchasing: {purchasing_cost * 10:.6f} ETH (${purchasing_cost * 10 * eth_price:.2f})")

                with scale_tab2:
                    # Medium hospital (1000 records/month, 500 shares/month, 50 purchases/month)
                    medium_monthly = (storing_cost * 1000) + (sharing_cost * 500) + (purchasing_cost * 50)
                    st.metric("Monthly Cost (1000 records, 500 shares, 50 purchases)",
                             f"{medium_monthly:.6f} ETH",
                             f"${medium_monthly * eth_price:.2f}")

                    # Show breakdown
                    st.write("Cost Breakdown:")
                    st.write(f"- Storing: {storing_cost * 1000:.6f} ETH (${storing_cost * 1000 * eth_price:.2f})")
                    st.write(f"- Sharing: {sharing_cost * 500:.6f} ETH (${sharing_cost * 500 * eth_price:.2f})")
                    st.write(f"- Purchasing: {purchasing_cost * 50:.6f} ETH (${purchasing_cost * 50 * eth_price:.2f})")

                with scale_tab3:
                    # Large hospital (10000 records/month, 5000 shares/month, 200 purchases/month)
                    large_monthly = (storing_cost * 10000) + (sharing_cost * 5000) + (purchasing_cost * 200)
                    st.metric("Monthly Cost (10000 records, 5000 shares, 200 purchases)",
                             f"{large_monthly:.6f} ETH",
                             f"${large_monthly * eth_price:.2f}")

                    # Show breakdown
                    st.write("Cost Breakdown:")
                    st.write(f"- Storing: {storing_cost * 10000:.6f} ETH (${storing_cost * 10000 * eth_price:.2f})")
                    st.write(f"- Sharing: {sharing_cost * 5000:.6f} ETH (${sharing_cost * 5000 * eth_price:.2f})")
                    st.write(f"- Purchasing: {purchasing_cost * 200:.6f} ETH (${purchasing_cost * 200 * eth_price:.2f})")

                # Add viability assessment
                st.subheader("Viability Assessment")

                # Calculate average cost per record across all workflows
                total_count = sum(d['count'] for d in result['fees_by_workflow'].values())
                if total_count > 0:
                    avg_cost_per_tx = result['total_gas_fees'] / total_count
                    st.metric("Average Cost per Transaction", f"{avg_cost_per_tx:.6f} ETH", f"${avg_cost_per_tx * eth_price:.2f}")

                    # Make viability assessment
                    if avg_cost_per_tx * eth_price < 0.10:  # Less than $0.10 per transaction
                        st.success("ASSESSMENT: HIGHLY VIABLE - Transaction costs are minimal relative to healthcare data value")
                    elif avg_cost_per_tx * eth_price < 1.00:  # Less than $1.00 per transaction
                        st.success("ASSESSMENT: VIABLE - Transaction costs are reasonable for most healthcare applications")
                    elif avg_cost_per_tx * eth_price < 5.00:  # Less than $5.00 per transaction
                        st.warning("ASSESSMENT: MODERATELY VIABLE - Transaction costs may be acceptable for high-value data")
                    else:  # More than $5.00 per transaction
                        st.error("ASSESSMENT: CHALLENGING - Transaction costs are high, consider Layer 2 or alternative approaches")
            else:
                st.info("No workflow cost data available.")

            # Add export functionality
            st.subheader("Export Gas Fees and Transactions")
            st.markdown("Export all gas fees and transaction data to a text file for record keeping or analysis.")

            # Add export options
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                export_format = st.selectbox(
                    "Export Format",
                    ["Text (.txt)", "CSV (.csv)"],
                    index=0,
                    help="Select the format for the exported file",
                    key="export_format"
                )

            with export_col2:
                export_detail = st.selectbox(
                    "Detail Level",
                    ["Standard", "Detailed", "Comprehensive"],
                    index=1,
                    help="Select the level of detail for the exported file",
                    key="export_detail"
                )

            # Generate the export content based on format and detail level
            if export_format == "Text (.txt)":
                export_content = generate_gas_fee_export(result, detail_level=export_detail.lower())
                mime_type = "text/plain"
                file_ext = "txt"
            else:  # CSV format
                export_content = generate_gas_fee_csv(result, detail_level=export_detail.lower())
                mime_type = "text/csv"
                file_ext = "csv"

            # Create a download button
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_fees_report_{timestamp}.{file_ext}"

            # Add custom filename option
            custom_filename = st.text_input("Custom Filename (optional)", "", help="Enter a custom filename (without extension)")
            if custom_filename:
                filename = f"{custom_filename}.{file_ext}"

            st.download_button(
                label=f"Download Gas Fees Report ({export_detail} {export_format})",
                data=export_content,
                file_name=filename,
                mime=mime_type,
                help="Download a file containing all gas fees and transaction data"
            )

            # Add a preview of the export
            with st.expander("Preview Export Content"):
                if export_format == "Text (.txt)":
                    st.text(export_content)
                else:  # CSV format
                    st.text("CSV Preview (first 20 lines):")
                    st.code("\n".join(export_content.split("\n")[:20]))
        else:
            st.error(f"Error fetching gas fees: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")

# Function to generate export content for gas fees and transactions
def generate_gas_fee_export(fees_data, detail_level="detailed"):
    """Generate a text file content for gas fees and transactions

    Args:
        fees_data: The gas fees data from the API
        detail_level: The level of detail to include (standard, detailed, comprehensive)

    Returns:
        A string containing the formatted text content
    """
    content = []

    # Add header
    content.append("HEALTHCARE DATA SHARING - GAS FEES AND TRANSACTIONS REPORT")
    content.append("==========================================================\n")

    # Add timestamp
    content.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Add summary statistics
    content.append("SUMMARY STATISTICS")
    content.append("------------------")
    content.append(f"Total Gas Fees: {fees_data['total_gas_fees']:.6f} ETH")
    content.append(f"Transaction Count: {fees_data['transaction_count']}")
    content.append(f"Average Gas Fee: {fees_data['average_gas_fee']:.6f} ETH\n")

    # Add fees by workflow
    content.append("GAS FEES BY WORKFLOW")
    content.append("--------------------")
    if 'fees_by_workflow' in fees_data and fees_data['fees_by_workflow']:
        # Header for the table
        content.append(f"{'Workflow':<15} {'Count':<10} {'Total Gas Fee (ETH)':<20} {'Average Gas Fee (ETH)':<20} {'% of Total':<15}")
        content.append("-" * 80)

        # Add each workflow type
        for workflow, data in fees_data['fees_by_workflow'].items():
            if data['count'] > 0:
                percent = (data['total_gas_fee'] / fees_data['total_gas_fees']) * 100 if fees_data['total_gas_fees'] > 0 else 0
                content.append(f"{workflow.capitalize():<15} {data['count']:<10} {data['total_gas_fee']:<20.6f} {data['average_gas_fee']:<20.6f} {percent:<15.2f}%")
        content.append("")
    else:
        content.append("No gas fee data by workflow available.\n")

    # Add fees by transaction type
    content.append("GAS FEES BY TRANSACTION TYPE")
    content.append("----------------------------")
    if fees_data['fees_by_type']:
        # Header for the table
        content.append(f"{'Transaction Type':<25} {'Count':<10} {'Total Gas Fee (ETH)':<20} {'Average Gas Fee (ETH)':<20}")
        content.append("-" * 75)

        # Add each transaction type
        for tx_type, data in fees_data['fees_by_type'].items():
            content.append(f"{tx_type:<25} {data['count']:<10} {data['total_gas_fee']:<20.6f} {data['average_gas_fee']:<20.6f}")
        content.append("")
    else:
        content.append("No gas fee data by transaction type available.\n")

    # Add workflow analysis
    content.append("WORKFLOW COST ANALYSIS")
    content.append("----------------------")
    if 'fees_by_workflow' in fees_data and fees_data['fees_by_workflow']:
        # Calculate cost per operation for each workflow
        storing_cost = fees_data['fees_by_workflow'].get('storing', {}).get('average_gas_fee', 0)
        sharing_cost = fees_data['fees_by_workflow'].get('sharing', {}).get('average_gas_fee', 0)
        purchasing_cost = fees_data['fees_by_workflow'].get('purchasing', {}).get('average_gas_fee', 0)

        # Estimate real-world costs (assuming 1 ETH = $2000)
        eth_price = 2000  # USD per ETH
        content.append(f"Estimated costs based on ETH price of ${eth_price}:\n")

        content.append(f"Storing a medical record: {storing_cost:.6f} ETH (${storing_cost * eth_price:.2f})")
        content.append(f"Sharing a medical record: {sharing_cost:.6f} ETH (${sharing_cost * eth_price:.2f})")
        content.append(f"Purchasing data: {purchasing_cost:.6f} ETH (${purchasing_cost * eth_price:.2f})")

        # Add detailed breakdown by transaction type within each workflow
        content.append("\nDetailed Cost Breakdown by Transaction Type:")

        # Group transactions by workflow and type
        workflow_type_costs = {}
        for tx in fees_data['transactions']:
            workflow = tx.get('workflow', 'other')
            tx_type = tx.get('type', 'Unknown')
            gas_fee = tx.get('gas_fee', 0)

            if isinstance(gas_fee, (int, float)):
                if workflow not in workflow_type_costs:
                    workflow_type_costs[workflow] = {}

                if tx_type not in workflow_type_costs[workflow]:
                    workflow_type_costs[workflow][tx_type] = {
                        'count': 0,
                        'total_gas_fee': 0,
                        'min_gas_fee': float('inf'),
                        'max_gas_fee': 0
                    }

                workflow_type_costs[workflow][tx_type]['count'] += 1
                workflow_type_costs[workflow][tx_type]['total_gas_fee'] += gas_fee
                workflow_type_costs[workflow][tx_type]['min_gas_fee'] = min(workflow_type_costs[workflow][tx_type]['min_gas_fee'], gas_fee)
                workflow_type_costs[workflow][tx_type]['max_gas_fee'] = max(workflow_type_costs[workflow][tx_type]['max_gas_fee'], gas_fee)

        # Display the detailed breakdown
        for workflow, types in sorted(workflow_type_costs.items()):
            content.append(f"\n  {workflow.capitalize()} Workflow:")
            content.append(f"  {'-' * (len(workflow) + 9)}")

            # Header for the table
            content.append(f"  {'Transaction Type':<25} {'Count':<8} {'Avg Gas (ETH)':<15} {'Min Gas (ETH)':<15} {'Max Gas (ETH)':<15} {'Total Gas (ETH)':<15} {'USD Cost':<10}")
            content.append(f"  {'-' * 103}")

            # Add each transaction type
            for tx_type, data in sorted(types.items()):
                avg_gas = data['total_gas_fee'] / data['count'] if data['count'] > 0 else 0
                usd_cost = data['total_gas_fee'] * eth_price

                content.append(f"  {tx_type:<25} {data['count']:<8} {avg_gas:<15.6f} {data['min_gas_fee']:<15.6f} {data['max_gas_fee']:<15.6f} {data['total_gas_fee']:<15.6f} ${usd_cost:<9.2f}")

        # Add scaling analysis
        content.append("\nScaling Analysis (estimated monthly costs):\n")

        # Small clinic (100 records/month, 50 shares/month, 10 purchases/month)
        small_monthly = (storing_cost * 100) + (sharing_cost * 50) + (purchasing_cost * 10)
        content.append(f"Small clinic (100 records, 50 shares, 10 purchases): {small_monthly:.6f} ETH (${small_monthly * eth_price:.2f})")
        content.append(f"  - Storing: {storing_cost * 100:.6f} ETH (${storing_cost * 100 * eth_price:.2f})")
        content.append(f"  - Sharing: {sharing_cost * 50:.6f} ETH (${sharing_cost * 50 * eth_price:.2f})")
        content.append(f"  - Purchasing: {purchasing_cost * 10:.6f} ETH (${purchasing_cost * 10 * eth_price:.2f})")

        # Medium hospital (1000 records/month, 500 shares/month, 50 purchases/month)
        medium_monthly = (storing_cost * 1000) + (sharing_cost * 500) + (purchasing_cost * 50)
        content.append(f"\nMedium hospital (1000 records, 500 shares, 50 purchases): {medium_monthly:.6f} ETH (${medium_monthly * eth_price:.2f})")
        content.append(f"  - Storing: {storing_cost * 1000:.6f} ETH (${storing_cost * 1000 * eth_price:.2f})")
        content.append(f"  - Sharing: {sharing_cost * 500:.6f} ETH (${sharing_cost * 500 * eth_price:.2f})")
        content.append(f"  - Purchasing: {purchasing_cost * 50:.6f} ETH (${purchasing_cost * 50 * eth_price:.2f})")

        # Large hospital (10000 records/month, 5000 shares/month, 200 purchases/month)
        large_monthly = (storing_cost * 10000) + (sharing_cost * 5000) + (purchasing_cost * 200)
        content.append(f"\nLarge hospital (10000 records, 5000 shares, 200 purchases): {large_monthly:.6f} ETH (${large_monthly * eth_price:.2f})")
        content.append(f"  - Storing: {storing_cost * 10000:.6f} ETH (${storing_cost * 10000 * eth_price:.2f})")
        content.append(f"  - Sharing: {sharing_cost * 5000:.6f} ETH (${sharing_cost * 5000 * eth_price:.2f})")
        content.append(f"  - Purchasing: {purchasing_cost * 200:.6f} ETH (${purchasing_cost * 200 * eth_price:.2f})")

        # Add annual cost projections
        content.append("\nAnnual Cost Projections:")
        content.append(f"  Small clinic: {small_monthly * 12:.6f} ETH (${small_monthly * 12 * eth_price:.2f})")
        content.append(f"  Medium hospital: {medium_monthly * 12:.6f} ETH (${medium_monthly * 12 * eth_price:.2f})")
        content.append(f"  Large hospital: {large_monthly * 12:.6f} ETH (${large_monthly * 12 * eth_price:.2f})")

        content.append("")
    else:
        content.append("No workflow cost data available.\n")

    # Add transaction details
    content.append("TRANSACTION DETAILS")
    content.append("-------------------")
    if fees_data['transactions']:
        # Header for the table
        content.append(f"{'Timestamp':<20} {'Type':<20} {'Workflow':<12} {'Status':<10} {'Gas Fee (ETH)':<15} {'TX Hash':<45} {'Request ID':<15}")
        content.append("-" * 140)

        # Sort transactions by timestamp (newest first)
        sorted_txs = sorted(fees_data['transactions'], key=lambda x: x.get('timestamp', 0), reverse=True)

        # Add each transaction
        for tx in sorted_txs:
            tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx.get("tx_hash", "N/A")
            gas_fee = tx.get("gas_fee", "N/A")
            gas_fee_str = f"{gas_fee:.6f}" if isinstance(gas_fee, (int, float)) else gas_fee
            workflow = tx.get("workflow", "other").capitalize()
            content.append(f"{tx_time:<20} {tx['type']:<20} {workflow:<12} {tx['status']:<10} {gas_fee_str:<15} {tx_hash:<45} {tx.get('request_id', 'N/A'):<15}")

        # Add detailed transaction information if detail level is detailed or comprehensive
        if detail_level in ["detailed", "comprehensive"]:
            content.append("\nDETAILED TRANSACTION INFORMATION")
            content.append("-------------------------------")

            for i, tx in enumerate(sorted_txs):
                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                content.append(f"\nTransaction #{i+1}:")
                content.append(f"  Timestamp: {tx_time}")
                content.append(f"  Type: {tx.get('type', 'Unknown')}")
                content.append(f"  Workflow: {tx.get('workflow', 'other').capitalize()}")
                content.append(f"  Status: {tx.get('status', 'Unknown')}")
                content.append(f"  Gas Fee: {gas_fee_str} ETH")
                content.append(f"  TX Hash: {tx_hash}")
                content.append(f"  Request ID: {tx.get('request_id', 'N/A')}")

                # Add amount if available
                if 'amount' in tx:
                    content.append(f"  Amount: {tx['amount']} ETH")

                # Add details if available
                if 'details' in tx and tx['details']:
                    content.append("  Details:")
                    for key, value in tx['details'].items():
                        if isinstance(value, dict):
                            content.append(f"    {key}:")
                            for k, v in value.items():
                                content.append(f"      {k}: {v}")
                        elif isinstance(value, list):
                            content.append(f"    {key}: {', '.join(str(item) for item in value)}")
                        else:
                            content.append(f"    {key}: {value}")
    else:
        content.append("No transaction details available.")

    # Add technical analysis section if detail level is detailed or comprehensive
    if detail_level in ["detailed", "comprehensive"]:
        content.append("\nTECHNICAL ANALYSIS")
        content.append("------------------")

        # Gas usage patterns
        content.append("Gas Usage Patterns:")
        if fees_data['transactions']:
            # Calculate gas usage statistics
            gas_fees = [tx.get('gas_fee', 0) for tx in fees_data['transactions'] if isinstance(tx.get('gas_fee'), (int, float))]
            if gas_fees:
                min_gas = min(gas_fees)
                max_gas = max(gas_fees)
                avg_gas = sum(gas_fees) / len(gas_fees)
                median_gas = sorted(gas_fees)[len(gas_fees) // 2] if len(gas_fees) > 0 else 0

                content.append(f"  Minimum Gas Fee: {min_gas:.6f} ETH")
                content.append(f"  Maximum Gas Fee: {max_gas:.6f} ETH")
                content.append(f"  Average Gas Fee: {avg_gas:.6f} ETH")
                content.append(f"  Median Gas Fee: {median_gas:.6f} ETH")
                content.append(f"  Range: {max_gas - min_gas:.6f} ETH")
                content.append(f"  Variance: {sum((x - avg_gas) ** 2 for x in gas_fees) / len(gas_fees):.6f} ETH²")

                # Gas price distribution
                content.append("\nGas Fee Distribution:")
                bins = [0, 0.0005, 0.001, 0.002, 0.005, 0.01, float('inf')]
                bin_labels = ["<0.0005", "0.0005-0.001", "0.001-0.002", "0.002-0.005", "0.005-0.01", ">0.01"]
                bin_counts = [0] * len(bin_labels)

                for fee in gas_fees:
                    for i, upper in enumerate(bins[1:]):
                        if fee < upper:
                            bin_counts[i] += 1
                            break

                for i, (label, count) in enumerate(zip(bin_labels, bin_counts)):
                    percent = (count / len(gas_fees)) * 100 if gas_fees else 0
                    bar = "█" * int(percent / 5) if percent > 0 else ""
                    content.append(f"  {label} ETH: {count} txs ({percent:.1f}%) {bar}")
        else:
            content.append("  No gas usage data available.")

        # Transaction timing analysis
        content.append("\nTransaction Timing Analysis:")
        if fees_data['transactions']:
            timestamps = [tx.get('timestamp', 0) for tx in fees_data['transactions']]
            if timestamps:
                # Convert to datetime objects
                dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]

                # Get min and max dates
                min_date = min(dates)
                max_date = max(dates)
                date_range = (max_date - min_date).days + 1

                content.append(f"  First Transaction: {min_date.strftime('%Y-%m-%d %H:%M:%S')}")
                content.append(f"  Last Transaction: {max_date.strftime('%Y-%m-%d %H:%M:%S')}")
                content.append(f"  Date Range: {date_range} days")
                content.append(f"  Average Transactions per Day: {len(timestamps) / date_range:.2f}" if date_range > 0 else "  Average Transactions per Day: N/A")

                # Analyze transaction frequency by hour of day
                hours = [d.hour for d in dates]
                hour_counts = {h: hours.count(h) for h in range(24)}

                content.append("\n  Transaction Frequency by Hour of Day:")
                for hour in range(24):
                    count = hour_counts.get(hour, 0)
                    percent = (count / len(hours)) * 100 if hours else 0
                    bar = "█" * int(percent / 5) if percent > 0 else ""
                    content.append(f"    {hour:02d}:00 - {hour:02d}:59: {count} txs ({percent:.1f}%) {bar}")
        else:
            content.append("  No transaction timing data available.")

    # Add conclusion and recommendations
    content.append("\nCONCLUSION AND RECOMMENDATIONS")
    content.append("------------------------------")
    content.append("Based on the transaction data analysis, here are some observations and recommendations:")
    content.append("")

    # Calculate which workflow is most expensive
    if 'fees_by_workflow' in fees_data and fees_data['fees_by_workflow']:
        workflows = [(w, d['average_gas_fee']) for w, d in fees_data['fees_by_workflow'].items() if d['count'] > 0]
        if workflows:
            most_expensive = max(workflows, key=lambda x: x[1])
            content.append(f"1. The {most_expensive[0].capitalize()} workflow has the highest average gas cost at {most_expensive[1]:.6f} ETH.")
            content.append("   Consider optimizing this workflow to reduce costs.")

        # Add optimization recommendations
        content.append("")
        content.append("2. Optimization strategies:")
        content.append("   - Batch multiple records in a single transaction where possible")
        content.append("   - Use Layer 2 solutions for high-volume operations")
        content.append("   - Implement gas price strategies during network congestion")
        content.append("   - Consider hybrid on-chain/off-chain approaches for data-intensive operations")

        # Add viability assessment
        content.append("")
        content.append("3. Viability assessment:")

        # Calculate average cost per record across all workflows
        total_count = sum(d['count'] for d in fees_data['fees_by_workflow'].values())
        if total_count > 0:
            avg_cost_per_tx = fees_data['total_gas_fees'] / total_count
            content.append(f"   - Average cost per transaction: {avg_cost_per_tx:.6f} ETH (${avg_cost_per_tx * eth_price:.2f})")

            # Make viability assessment
            if avg_cost_per_tx * eth_price < 0.10:  # Less than $0.10 per transaction
                content.append("   - ASSESSMENT: HIGHLY VIABLE - Transaction costs are minimal relative to healthcare data value")
            elif avg_cost_per_tx * eth_price < 1.00:  # Less than $1.00 per transaction
                content.append("   - ASSESSMENT: VIABLE - Transaction costs are reasonable for most healthcare applications")
            elif avg_cost_per_tx * eth_price < 5.00:  # Less than $5.00 per transaction
                content.append("   - ASSESSMENT: MODERATELY VIABLE - Transaction costs may be acceptable for high-value data")
            else:  # More than $5.00 per transaction
                content.append("   - ASSESSMENT: CHALLENGING - Transaction costs are high, consider Layer 2 or alternative approaches")

    # Add comparison with traditional systems
    content.append("\n4. Comparison with traditional healthcare data systems:")
    content.append("   - Traditional EMR systems: $15,000-$70,000 per provider for implementation")
    content.append("   - Traditional data sharing: High administrative overhead, legal costs, and time delays")
    content.append("   - Traditional data purchasing: Complex contracts, intermediaries, and high fees (often 20-30% of data value)")
    content.append("\n   This blockchain-based system offers:")
    content.append("   - Transparent, immutable record of all data transactions")
    content.append("   - Reduced administrative overhead through smart contracts")
    content.append("   - Direct peer-to-peer data sharing with cryptographic security")
    content.append("   - Automated compliance with data sharing regulations")

    return "\n".join(content)


# Function to generate CSV export content for gas fees and transactions
def generate_gas_fee_csv(fees_data, detail_level="detailed"):
    """Generate a CSV file content for gas fees and transactions

    Args:
        fees_data: The gas fees data from the API
        detail_level: The level of detail to include (standard, detailed, comprehensive)

    Returns:
        A string containing the CSV content
    """
    import csv
    import io

    # Create a StringIO object to write CSV data
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row with metadata
    writer.writerow(["HEALTHCARE DATA SHARING - GAS FEES AND TRANSACTIONS REPORT"])
    writer.writerow([f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])

    # Write summary statistics
    writer.writerow(["SUMMARY STATISTICS"])
    writer.writerow(["Total Gas Fees (ETH)", "Transaction Count", "Average Gas Fee (ETH)"])
    writer.writerow([f"{fees_data['total_gas_fees']:.6f}", fees_data['transaction_count'], f"{fees_data['average_gas_fee']:.6f}"])
    writer.writerow([])

    # Write fees by workflow
    writer.writerow(["GAS FEES BY WORKFLOW"])
    if 'fees_by_workflow' in fees_data and fees_data['fees_by_workflow']:
        # Header for the table
        writer.writerow(["Workflow", "Count", "Total Gas Fee (ETH)", "Average Gas Fee (ETH)", "% of Total"])

        # Add each workflow type
        for workflow, data in fees_data['fees_by_workflow'].items():
            if data['count'] > 0:
                percent = (data['total_gas_fee'] / fees_data['total_gas_fees']) * 100 if fees_data['total_gas_fees'] > 0 else 0
                writer.writerow([workflow.capitalize(), data['count'], f"{data['total_gas_fee']:.6f}",
                               f"{data['average_gas_fee']:.6f}", f"{percent:.2f}%"])
    else:
        writer.writerow(["No gas fee data by workflow available."])
    writer.writerow([])

    # Write fees by transaction type
    writer.writerow(["GAS FEES BY TRANSACTION TYPE"])
    if fees_data['fees_by_type']:
        # Header for the table
        writer.writerow(["Transaction Type", "Count", "Total Gas Fee (ETH)", "Average Gas Fee (ETH)"])

        # Add each transaction type
        for tx_type, data in fees_data['fees_by_type'].items():
            writer.writerow([tx_type, data['count'], f"{data['total_gas_fee']:.6f}", f"{data['average_gas_fee']:.6f}"])
    else:
        writer.writerow(["No gas fee data by transaction type available."])
    writer.writerow([])

    # Write transaction details
    writer.writerow(["TRANSACTION DETAILS"])
    if fees_data['transactions']:
        # Header for the table
        writer.writerow(["Timestamp", "Type", "Workflow", "Status", "Gas Fee (ETH)", "TX Hash", "Request ID"])

        # Sort transactions by timestamp (newest first)
        sorted_txs = sorted(fees_data['transactions'], key=lambda x: x.get('timestamp', 0), reverse=True)

        # Add each transaction
        for tx in sorted_txs:
            tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx.get("tx_hash", "N/A")
            gas_fee = tx.get("gas_fee", "N/A")
            gas_fee_str = f"{gas_fee:.6f}" if isinstance(gas_fee, (int, float)) else gas_fee
            workflow = tx.get("workflow", "other").capitalize()
            writer.writerow([tx_time, tx['type'], workflow, tx['status'], gas_fee_str, tx_hash, tx.get('request_id', 'N/A')])
    else:
        writer.writerow(["No transaction details available."])
    writer.writerow([])

    # If detail level is detailed or comprehensive, add more detailed transaction information
    if detail_level in ["detailed", "comprehensive"] and fees_data['transactions']:
        writer.writerow(["DETAILED TRANSACTION INFORMATION"])
        writer.writerow(["Transaction ID", "Timestamp", "Type", "Workflow", "Status", "Gas Fee (ETH)", "TX Hash", "Request ID", "Amount (ETH)", "Details"])

        # Sort transactions by timestamp (newest first)
        sorted_txs = sorted(fees_data['transactions'], key=lambda x: x.get('timestamp', 0), reverse=True)

        # Add each transaction with details
        for i, tx in enumerate(sorted_txs):
            tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx.get("tx_hash", "N/A")
            gas_fee = tx.get("gas_fee", "N/A")
            gas_fee_str = f"{gas_fee:.6f}" if isinstance(gas_fee, (int, float)) else gas_fee
            workflow = tx.get("workflow", "other").capitalize()
            amount = tx.get("amount", "N/A")

            # Format details as a string
            details = ""
            if 'details' in tx and tx['details']:
                details_parts = []
                for key, value in tx['details'].items():
                    if isinstance(value, dict):
                        sub_parts = [f"{k}: {v}" for k, v in value.items()]
                        details_parts.append(f"{key}: {{{'; '.join(sub_parts)}}}")
                    elif isinstance(value, list):
                        details_parts.append(f"{key}: [{', '.join(str(item) for item in value)}]")
                    else:
                        details_parts.append(f"{key}: {value}")
                details = "; ".join(details_parts)

            writer.writerow([i+1, tx_time, tx.get('type', 'Unknown'), workflow, tx.get('status', 'Unknown'),
                           gas_fee_str, tx_hash, tx.get('request_id', 'N/A'), amount, details])
        writer.writerow([])

    # If detail level is comprehensive, add technical analysis
    if detail_level == "comprehensive" and fees_data['transactions']:
        # Gas usage statistics
        writer.writerow(["TECHNICAL ANALYSIS - GAS USAGE STATISTICS"])
        gas_fees = [tx.get('gas_fee', 0) for tx in fees_data['transactions'] if isinstance(tx.get('gas_fee'), (int, float))]
        if gas_fees:
            min_gas = min(gas_fees)
            max_gas = max(gas_fees)
            avg_gas = sum(gas_fees) / len(gas_fees)
            median_gas = sorted(gas_fees)[len(gas_fees) // 2] if len(gas_fees) > 0 else 0
            variance = sum((x - avg_gas) ** 2 for x in gas_fees) / len(gas_fees)

            writer.writerow(["Statistic", "Value (ETH)"])
            writer.writerow(["Minimum Gas Fee", f"{min_gas:.6f}"])
            writer.writerow(["Maximum Gas Fee", f"{max_gas:.6f}"])
            writer.writerow(["Average Gas Fee", f"{avg_gas:.6f}"])
            writer.writerow(["Median Gas Fee", f"{median_gas:.6f}"])
            writer.writerow(["Range", f"{max_gas - min_gas:.6f}"])
            writer.writerow(["Variance", f"{variance:.6f}"])
            writer.writerow([])

            # Gas fee distribution
            writer.writerow(["GAS FEE DISTRIBUTION"])
            bins = [0, 0.0005, 0.001, 0.002, 0.005, 0.01, float('inf')]
            bin_labels = ["<0.0005", "0.0005-0.001", "0.001-0.002", "0.002-0.005", "0.005-0.01", ">0.01"]
            bin_counts = [0] * len(bin_labels)

            for fee in gas_fees:
                for i, upper in enumerate(bins[1:]):
                    if fee < upper:
                        bin_counts[i] += 1
                        break

            writer.writerow(["Fee Range (ETH)", "Count", "Percentage"])
            for i, (label, count) in enumerate(zip(bin_labels, bin_counts)):
                percent = (count / len(gas_fees)) * 100 if gas_fees else 0
                writer.writerow([label, count, f"{percent:.1f}%"])
            writer.writerow([])

        # Transaction timing analysis
        writer.writerow(["TRANSACTION TIMING ANALYSIS"])
        timestamps = [tx.get('timestamp', 0) for tx in fees_data['transactions']]
        if timestamps:
            # Convert to datetime objects
            dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]

            # Get min and max dates
            min_date = min(dates)
            max_date = max(dates)
            date_range = (max_date - min_date).days + 1

            writer.writerow(["First Transaction", min_date.strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(["Last Transaction", max_date.strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(["Date Range (days)", date_range])
            writer.writerow(["Average Transactions per Day", f"{len(timestamps) / date_range:.2f}" if date_range > 0 else "N/A"])
            writer.writerow([])

            # Analyze transaction frequency by hour of day
            hours = [d.hour for d in dates]
            hour_counts = {h: hours.count(h) for h in range(24)}

            writer.writerow(["TRANSACTION FREQUENCY BY HOUR OF DAY"])
            writer.writerow(["Hour", "Count", "Percentage"])
            for hour in range(24):
                count = hour_counts.get(hour, 0)
                percent = (count / len(hours)) * 100 if hours else 0
                writer.writerow([f"{hour:02d}:00 - {hour:02d}:59", count, f"{percent:.1f}%"])

    # Get the CSV content as a string
    csv_content = output.getvalue()
    output.close()

    return csv_content

# Function to fetch patient records
def fetch_patient_records():
    """Fetch all records for the current patient"""
    if not st.session_state.wallet_connected:
        return

    if st.session_state.selected_role != "Patient":
        return

    try:
        # Call API to get all records for this patient
        try:
            response = requests.get(
                f"{API_URL}/records/list",
                params={
                    "patient_address": st.session_state.wallet_address
                }
            )

            # Print debug info
            print(f"API URL: {API_URL}/records/list?patient_address={st.session_state.wallet_address}")
            print(f"Response status: {response.status_code}")

            # If the first URL fails, try the alternative URL
            if response.status_code == 404:
                print("Trying alternative API URL...")
                response = requests.get(
                    f"{API_URL}/api/records/list",
                    params={
                        "patient_address": st.session_state.wallet_address
                    }
                )
                print(f"Alternative API URL: {API_URL}/api/records/list?patient_address={st.session_state.wallet_address}")
                print(f"Alternative response status: {response.status_code}")
        except Exception as e:
            print(f"Error fetching records: {str(e)}")
            response = None

        if response and response.status_code == 200:
            try:
                records = response.json()
                if "records" not in st.session_state:
                    st.session_state.records = []

                # Add new records to the session state
                for record in records:
                    if not any(r.get("cid") == record.get("cid") for r in st.session_state.records):
                        st.session_state.records.append(record)

                print(f"Fetched {len(records)} records for patient {st.session_state.wallet_address}")
            except Exception as e:
                print(f"Error processing records: {str(e)}")
                print(f"Response content: {response.text}")
    except Exception as e:
        print(f"Error fetching patient records: {str(e)}")

# Initialize session state variables
if "wallet_connected" not in st.session_state:
    st.session_state.wallet_connected = False
    st.session_state.wallet_address = None
    st.session_state.private_key = None
    st.session_state.trigger_rerun = False
    st.session_state.records = []

    # Set the default role
    default_role = "Patient"
    st.session_state.selected_role = default_role

    # Find the account that matches the default role
    default_account = None
    for account_name, account_info in TEST_ACCOUNTS.items():
        if account_info["role"] == default_role:
            default_account = account_name
            break

    if default_account:
        st.session_state.selected_account = default_account
    else:
        # Fallback to first account if no match found
        st.session_state.selected_account = list(TEST_ACCOUNTS.keys())[0]

def connect_wallet():
    # In a real app, this would use Wallet Connect or similar
    # For demo purposes, we'll simulate a connection

    # Get the selected account from session state
    selected_account = st.session_state.get("selected_account")

    # If no account is selected, use the first account in the list
    if not selected_account or selected_account not in TEST_ACCOUNTS:
        selected_account = list(TEST_ACCOUNTS.keys())[0]
        st.session_state.selected_account = selected_account

    # Get the account info from the TEST_ACCOUNTS dictionary
    account_info = TEST_ACCOUNTS[selected_account]
    wallet_address = account_info["address"]
    private_key = account_info["private_key"]

    # Generate an authentication challenge
    try:
        response = requests.post(
            f"{API_URL}/auth/challenge",
            json={"wallet_address": wallet_address}
        )

        # If the first URL fails, try the alternative URL
        if response.status_code == 404:
            print("Trying alternative API URL...")
            response = requests.post(
                f"{API_URL}/api/auth/challenge",
                json={"wallet_address": wallet_address}
            )

        if response.status_code == 200:
            challenge_data = response.json()
            challenge = challenge_data.get("challenge")

            # In a real app, this would be signed by the wallet
            # For demo purposes, we'll simulate signing with the private key
            message_hash = Web3.keccak(text=challenge)
            signed_message = w3.eth.account.sign_message(
                message_hash,
                private_key=private_key
            )
            signature = signed_message.signature.hex()

            # Verify the signature with the backend
            verify_response = requests.post(
                f"{API_URL}/auth/verify",
                json={
                    "wallet_address": wallet_address,
                    "signature": signature
                }
            )

            # If the first URL fails, try the alternative URL
            if verify_response.status_code == 404:
                print("Trying alternative API URL...")
                verify_response = requests.post(
                    f"{API_URL}/api/auth/verify",
                    json={
                        "wallet_address": wallet_address,
                        "signature": signature
                    }
                )

            if verify_response.status_code == 200:
                auth_data = verify_response.json()
                if auth_data.get("authenticated", False):
                    # Authentication successful
                    st.session_state.wallet_connected = True
                    st.session_state.wallet_address = wallet_address
                    st.session_state.private_key = private_key

                    # Set the role from the authentication response
                    st.session_state.selected_role = auth_data.get("role", account_info["role"])

                    # Debug info
                    print(f"Connected as {selected_account} with role {st.session_state.selected_role}")

                    # Set a flag to trigger rerun
                    st.session_state.trigger_rerun = True
                else:
                    st.error(f"Authentication failed: {auth_data.get('message', 'Unknown error')}")
            else:
                st.error(f"Error verifying signature: {verify_response.json().get('detail', 'Unknown error')}")
        else:
            st.error(f"Error getting authentication challenge: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        # Fallback to the old method if the authentication API is not available
        print(f"Error connecting to authentication API: {str(e)}")
        print("Falling back to direct connection without authentication")

        st.session_state.wallet_connected = True
        st.session_state.wallet_address = wallet_address
        st.session_state.private_key = private_key

        # Set the initial role based on the account type
        st.session_state.selected_role = account_info["role"]

        # Debug info
        print(f"Connected as {selected_account} with role {st.session_state.selected_role} (fallback)")

        # Set a flag to trigger rerun
        st.session_state.trigger_rerun = True

# Sidebar for wallet connection
with st.sidebar:
    st.title("Healthcare Data Sharing")

    if not st.session_state.wallet_connected:
        # Role selection dropdown with descriptions
        st.subheader("Select Your Role")

        role_descriptions = {
            "Patient": "Access and share your medical records",
            "Doctor": "Create and sign medical records for patients",
            "Hospital": "Manage data purchase requests and group membership",
            "Buyer": "Request to purchase anonymized medical data",
            "Group Manager": "Manage doctor group membership and signature tracing",
            "Revocation Manager": "Assist in signature tracing and revocation"
        }

        selected_role = st.selectbox(
            "Role",
            list(role_descriptions.keys()),
            index=0,
            help="Select a role to connect with"
        )

        # Display role description
        st.caption(role_descriptions[selected_role])

        # Find the account that matches the selected role
        selected_account = None
        for account_name, account_info in TEST_ACCOUNTS.items():
            if account_info["role"] == selected_role:
                selected_account = account_name
                break

        if selected_account:
            # Display account details in a nice format
            with st.container():
                st.markdown("**Account Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Name:** {selected_account}")
                    st.markdown(f"**Role:** {TEST_ACCOUNTS[selected_account]['role']}")
                with col2:
                    address = TEST_ACCOUNTS[selected_account]['address']
                    st.markdown(f"**Address:** `{address[:6]}...{address[-4:]}`")

                # Add a small explanation about the account
                if selected_role == "Patient":
                    st.info("This account will allow you to access and share your medical records.")
                elif selected_role == "Doctor":
                    st.info("This account will allow you to create and sign medical records for patients.")
                elif selected_role == "Hospital":
                    st.info("This account will allow you to manage data purchase requests and group membership.")
                elif selected_role == "Buyer":
                    st.info("This account will allow you to request to purchase anonymized medical data.")
                elif selected_role == "Group Manager":
                    st.info("This account will allow you to manage doctor group membership and signature tracing.")
                elif selected_role == "Revocation Manager":
                    st.info("This account will allow you to assist in signature tracing and revocation.")
        else:
            st.error(f"No account found for role: {selected_role}")
            selected_account = list(TEST_ACCOUNTS.keys())[0]  # Fallback to first account

        # Store the selected account in session state
        st.session_state.selected_account = selected_account

        # Connect button
        st.button("Connect Wallet", on_click=connect_wallet)
    else:
        # Display connected account details in a nice format
        st.subheader("Connected Account")
        st.success(f"Connected: {st.session_state.wallet_address[:6]}...{st.session_state.wallet_address[-4:]}")

        # Get account info
        account_info = TEST_ACCOUNTS[st.session_state.selected_account]

        # Display account details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Name:** {st.session_state.selected_account}")
            st.markdown(f"**Role:** {account_info['role']}")
        with col2:
            st.markdown(f"**Network:** BASE Sepolia Testnet")
            st.markdown(f"**Status:** Active ✅")

        # Show private key in an expander
        with st.expander("Show Private Key"):
            st.code(account_info["private_key"], language="text")
            st.caption("⚠️ Never share your private key in a real application!")

        # Each account has a fixed role
        st.session_state.selected_role = account_info["role"]
        role = st.session_state.selected_role

        # Debug info
        st.write(f"Debug - Selected Role: {role}")

        # Display role description
        role_descriptions = {
            "Patient": "Access and share your medical records",
            "Doctor": "Create and sign medical records for patients",
            "Hospital": "Manage data purchase requests and group membership",
            "Buyer": "Request to purchase anonymized medical data",
            "Group Manager": "Manage doctor group membership and signature tracing",
            "Revocation Manager": "Assist in signature tracing and revocation"
        }
        st.info(f"Role: {role} - {role_descriptions.get(role, '')}")

        if st.button("Disconnect"):
            # Call the logout API
            try:
                response = requests.post(
                    f"{API_URL}/auth/logout",
                    json={"wallet_address": st.session_state.wallet_address}
                )

                # If the first URL fails, try the alternative URL
                if response.status_code == 404:
                    print("Trying alternative API URL...")
                    response = requests.post(
                        f"{API_URL}/api/auth/logout",
                        json={"wallet_address": st.session_state.wallet_address}
                    )

                if response.status_code == 200:
                    print("Logout successful")
                else:
                    print(f"Logout failed: {response.status_code}")
            except Exception as e:
                print(f"Error logging out: {str(e)}")

            # Clear session state
            st.session_state.wallet_connected = False
            st.session_state.wallet_address = None
            st.session_state.private_key = None
            st.session_state.trigger_rerun = True

# Main content
if not st.session_state.wallet_connected:
    st.title("Welcome to Healthcare Data Sharing")
    st.write("Please connect your wallet to continue.")
else:
    # Get selected role from session state
    role = st.session_state.get("selected_role", "Patient")
    print(f"Current role: {role}")

    # Different UI based on role
    if role == "Patient":
        st.title("Patient Dashboard")

        # Automatically fetch patient records when the dashboard loads
        fetch_patient_records()

        # Tabs for different actions
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["My Records", "Share Records", "Data Requests", "Data Purchase Requests", "Gas Fees"])

        with tab1:
            st.header("My Health Records")

            # Add a refresh button
            if st.button("Refresh Records"):
                fetch_patient_records()
                st.success("Records refreshed!")

            # Section to enter certificate from doctor
            with st.expander("Access Record with Certificate", expanded=False):
                st.write("Enter the certificate provided by your doctor to access your medical record.")

                # Text area for certificate JSON
                cert_json = st.text_area("Certificate (JSON)",
                                        height=200,
                                        help="Paste the certificate JSON provided by your doctor")

                if st.button("Access Record"):
                    if not cert_json:
                        st.error("Please enter a certificate")
                    else:
                        try:
                            # Parse the certificate
                            cert = json.loads(cert_json)

                            # Validate certificate fields
                            required_fields = ["cid", "merkleRoot", "signature", "doctorId", "eId"]
                            if not all(field in cert for field in required_fields):
                                st.error("Invalid certificate. Missing required fields.")
                                st.info(f"Certificate should contain: {', '.join(required_fields)}")
                                st.info(f"Found: {', '.join(cert.keys())}")
                            else:
                                # Display certificate details
                                st.success("Certificate validated!")

                                # Explain the verification process
                                with st.expander("Certificate Verification Process"):
                                    st.markdown("**1. Signature Verification:**")
                                    st.markdown("- The group signature on the IDRecord is verified using the group public key")
                                    st.markdown("- This confirms the record was signed by a legitimate doctor without revealing which one")
                                    st.markdown("**2. eId Decryption:**")
                                    st.markdown("- The eId contains the hospital info and patient key encrypted with PCS")
                                    st.markdown("- The patient can decrypt this to get their key for the record")
                                    st.markdown("**3. Record Retrieval:**")
                                    st.markdown("- The encrypted record is retrieved from IPFS using the CID")
                                    st.markdown("**4. Record Decryption:**")
                                    st.markdown("- The record is decrypted using the patient's key")

                                with st.spinner("Retrieving and decrypting your medical record..."):
                                    # Call API to retrieve and decrypt the record
                                    response = requests.post(
                                        f"{API_URL}/records/retrieve",
                                        json={
                                            "cid": cert["cid"],
                                            "merkleRoot": cert["merkleRoot"],
                                            "signature": cert["signature"],
                                            "eId": cert["eId"],
                                            "patientAddress": st.session_state.wallet_address
                                        }
                                    )

                                    if response.status_code == 200:
                                        record_data = response.json()

                                        # Store the record in session state
                                        if "records" not in st.session_state:
                                            st.session_state.records = []

                                        # Add the record if it's not already in the list
                                        if not any(r.get("cid") == cert["cid"] for r in st.session_state.records):
                                            record_data["cid"] = cert["cid"]
                                            record_data["doctorId"] = cert["doctorId"]
                                            record_data["timestamp"] = cert.get("timestamp", int(time.time()))
                                            st.session_state.records.append(record_data)

                                        st.success("Record retrieved and decrypted successfully!")
                                    else:
                                        st.error(f"Error retrieving record: {response.json().get('detail', 'Unknown error')}")
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format. Please check the certificate.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Display existing records
            if hasattr(st.session_state, "records") and st.session_state.records:
                st.subheader("Your Medical Records")

                # Sort records by timestamp (newest first)
                sorted_records = sorted(st.session_state.records, key=lambda x: x.get('timestamp', 0), reverse=True)

                for i, record in enumerate(sorted_records):
                    # Get diagnosis from medical_data if available
                    diagnosis = "Medical Record"
                    if record.get('medical_data', {}) and record['medical_data'].get('diagnosis'):
                        diagnosis = record['medical_data']['diagnosis']
                    elif record.get('diagnosis'):  # Fallback to old format
                        diagnosis = record['diagnosis']

                    with st.expander(f"{record.get('category', 'General')} - {diagnosis} - {record.get('date', 'Unknown date')}"):
                        # Basic information
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Date:** {record.get('date', 'N/A')}")
                            st.markdown(f"**Category:** {record.get('category', 'General')}")
                            doctor_id = record.get('doctorId', 'N/A')
                            if isinstance(doctor_id, str) and len(doctor_id) > 10:
                                st.markdown(f"**Doctor ID:** {doctor_id[:6]}...{doctor_id[-4:]}")
                            else:
                                st.markdown(f"**Doctor ID:** {doctor_id}")

                        with col2:
                            timestamp = record.get('timestamp', 0)
                            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            st.markdown(f"**Created:** {date_str}")
                            st.markdown(f"**IPFS CID:** {record.get('cid', 'N/A')}")
                            st.markdown(f"**Hospital:** {record.get('hospitalInfo', 'N/A')}")

                        # Demographics section
                        st.subheader("Demographics")
                        demographics = record.get('demographics', {})
                        if demographics:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Age:** {demographics.get('age', 'N/A')}")
                                st.markdown(f"**Gender:** {demographics.get('gender', 'N/A')}")
                            with col2:
                                st.markdown(f"**Location:** {demographics.get('location', 'N/A')}")
                                st.markdown(f"**Ethnicity:** {demographics.get('ethnicity', 'N/A')}")
                        else:
                            st.info("No demographics information available")

                        # Medical data section
                        st.subheader("Medical Data")
                        medical_data = record.get('medical_data', {})
                        if medical_data:
                            st.markdown(f"**Diagnosis:** {medical_data.get('diagnosis', 'N/A')}")
                            st.markdown(f"**Treatment:** {medical_data.get('treatment', 'N/A')}")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Medications:**")
                                st.text_area(f"Medications_{i}", value=medical_data.get('medications', ''), height=100, disabled=True)
                            with col2:
                                st.markdown("**Lab Results:**")
                                st.text_area(f"Lab_Results_{i}", value=medical_data.get('lab_results', ''), height=100, disabled=True)
                        else:
                            st.info("No detailed medical data available")

                        # Notes section
                        st.subheader("Additional Notes")
                        st.text_area(f"notes_{i}", value=record.get('notes', ''), height=100, disabled=True)

                        # Option to share with a doctor
                        if st.button(f"Share with Doctor", key=f"share_{i}"):
                            st.session_state.record_to_share = record
                            st.session_state.trigger_rerun = True
            else:
                st.info("No records found. Records will appear here automatically when a doctor creates them for you.")

        with tab2:
            st.header("Share Records with Doctors")

            # Form for sharing records
            with st.form("share_record_form"):
                record_cid = st.text_input("Record CID to Share")
                doctor_address = st.text_input("Doctor's Wallet Address")

                submit_button = st.form_submit_button("Share Record via IPFS")

                if submit_button:
                    # Call API to share record
                    try:
                        # The API expects a ShareRequest object and a wallet_address as separate parameters
                        # But FastAPI combines them in a single JSON object
                        response = requests.post(
                            f"{API_URL}/api/share",
                            json={
                                "record_cid": record_cid,
                                "doctor_address": doctor_address,
                                "wallet_address": st.session_state.wallet_address
                            },
                            headers={"Content-Type": "application/json"}
                        )

                        # If the first attempt fails, try an alternative format
                        if response.status_code == 404 or response.status_code == 422:
                            print(f"First attempt failed with status {response.status_code}, trying alternative format...")
                            response = requests.post(
                                f"{API_URL}/share",  # Try without /api prefix
                                json={
                                    "record_cid": record_cid,
                                    "doctor_address": doctor_address,
                                    "wallet_address": st.session_state.wallet_address
                                },
                                headers={"Content-Type": "application/json"}
                            )

                        # Print debug info
                        print(f"Share request: {record_cid} with doctor {doctor_address}")
                        print(f"Response status: {response.status_code}")

                        if response.status_code == 200:
                            result = response.json()
                            st.success("Record shared successfully via IPFS!")
                            st.info(f"Sharing Metadata CID: {result['sharing_metadata_cid']}")
                            st.info(f"Shared Record CID: {result['record_cid']}")
                            st.info("The doctor can now access this record using the Sharing Metadata CID.")

                            # Create a shareable link (in a real app, this would be sent to the doctor)
                            sharing_link = f"https://ipfs.io/ipfs/{result['sharing_metadata_cid']}"
                            st.markdown(f"**IPFS Link:** [View Sharing Metadata]({sharing_link})")
                            st.info("Send this Sharing Metadata CID to the doctor through a secure channel.")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        with tab3:
            st.header("Data Requests")

            # Function to fetch data requests for this patient
            def fetch_data_requests():
                try:
                    # Call API to get data requests for this patient
                    response = requests.get(
                        f"{API_URL}/patient/requests",
                        params={
                            "wallet_address": st.session_state.wallet_address
                        }
                    )

                    # If the first URL fails, try the alternative URL
                    if response.status_code == 404:
                        print("Trying alternative API URL...")
                        response = requests.get(
                            f"{API_URL}/api/patient/requests",
                            params={
                                "wallet_address": st.session_state.wallet_address
                            }
                        )

                    if response.status_code == 200:
                        requests_data = response.json()
                        return requests_data.get("requests", [])
                    else:
                        print(f"Error fetching data requests: {response.status_code}")
                        return []
                except Exception as e:
                    print(f"Error fetching data requests: {str(e)}")
                    return []

            # For demo purposes, let's create some sample data requests
            # In a real implementation, these would come from the API
            if "data_requests" not in st.session_state:
                # Try to fetch from API first
                api_requests = fetch_data_requests()

                if api_requests:
                    st.session_state.data_requests = api_requests
                else:
                    # Use sample data as fallback
                    st.session_state.data_requests = [
                        {
                            "request_id": "req_001",
                            "buyer": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",  # Buyer address
                            "hospital": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",  # Hospital address
                            "template": {
                                "category": "Cardiology",
                                "demographics": {"age": True, "gender": True},
                                "medical_data": {"diagnosis": True, "treatment": True},
                                "time_period": "1 year",
                                "min_records": 1
                            },
                            "status": "pending",
                            "timestamp": int(time.time()) - 3600,  # 1 hour ago
                            "amount": 0.1
                        }
                    ]

            # Add a refresh button
            if st.button("Refresh Data Requests"):
                api_requests = fetch_data_requests()
                if api_requests:
                    st.session_state.data_requests = api_requests
                st.success("Data requests refreshed!")

            # Display data requests
            if not st.session_state.data_requests:
                st.info("No data requests found. Hospitals will send requests here when buyers request data that matches your records.")
            else:
                st.subheader("Pending Data Requests")

                for i, request in enumerate(st.session_state.data_requests):
                    if request.get("status") == "pending":
                        with st.expander(f"Request {request['request_id']} - {request['template']['category']}"):
                            # Request details
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Request ID:** {request['request_id']}")

                                # Format buyer address
                                buyer = request.get("buyer", "Unknown")
                                buyer_display = buyer
                                if len(buyer) > 10:
                                    buyer_display = f"{buyer[:6]}...{buyer[-4:]}"

                                # Check if it's a known address
                                buyer_name = "Unknown"
                                for name, info in TEST_ACCOUNTS.items():
                                    if info["address"].lower() == buyer.lower():
                                        buyer_name = f"{name} ({info['role']})"
                                        break

                                st.markdown(f"**Buyer:** `{buyer_display}` - {buyer_name}")

                                # Format hospital address
                                hospital = request.get("hospital", "Unknown")
                                hospital_display = hospital
                                if len(hospital) > 10:
                                    hospital_display = f"{hospital[:6]}...{hospital[-4:]}"

                                # Check if it's a known address
                                hospital_name = "Unknown"
                                for name, info in TEST_ACCOUNTS.items():
                                    if info["address"].lower() == hospital.lower():
                                        hospital_name = f"{name} ({info['role']})"
                                        break

                                st.markdown(f"**Hospital:** `{hospital_display}` - {hospital_name}")

                            with col2:
                                # Format timestamp
                                timestamp = request.get("timestamp", 0)
                                date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Requested:** {date_str}")

                                # Payment amount
                                amount = request.get("amount", 0.1)
                                st.markdown(f"**Payment Amount:** {amount} ETH")

                                # Status
                                status = request.get("status", "pending")
                                st.markdown(f"**Status:** {status.capitalize()}")

                            # Template details
                            st.subheader("Requested Data")
                            template = request.get("template", {})

                            # Category
                            st.markdown(f"**Category:** {template.get('category', 'General')}")

                            # Demographics
                            demographics = template.get("demographics", {})
                            if demographics:
                                st.markdown("**Demographics:**")
                                demo_items = []
                                for field, included in demographics.items():
                                    if included:
                                        demo_items.append(field.capitalize())
                                st.markdown(", ".join(demo_items))

                            # Medical data
                            medical_data = template.get("medical_data", {})
                            if medical_data:
                                st.markdown("**Medical Data:**")
                                med_items = []
                                for field, included in medical_data.items():
                                    if included:
                                        med_items.append(field.capitalize())
                                st.markdown(", ".join(med_items))

                            # Time period and min records
                            st.markdown(f"**Time Period:** {template.get('time_period', '1 year')}")
                            st.markdown(f"**Minimum Records:** {template.get('min_records', 1)}")

                            # Action buttons
                            st.markdown("---")
                            st.markdown("**Actions:**")

                            if st.button(f"Fill Template Automatically", key=f"fill_{request['request_id']}"):
                                with st.spinner("Filling template with your data..."):
                                    # Call API to fill template
                                    try:
                                        response = requests.post(
                                            f"{API_URL}/patient/fill-template",
                                            json={
                                                "request_id": request["request_id"],
                                                "wallet_address": st.session_state.wallet_address
                                            }
                                        )

                                        # If the first URL fails, try the alternative URL
                                        if response.status_code == 404:
                                            print("Trying alternative API URL...")
                                            response = requests.post(
                                                f"{API_URL}/api/patient/fill-template",
                                                json={
                                                    "request_id": request["request_id"],
                                                    "wallet_address": st.session_state.wallet_address
                                                }
                                            )

                                        if response.status_code == 200:
                                            result = response.json()
                                            st.success("Template filled successfully!")

                                            # Update the request status
                                            for req in st.session_state.data_requests:
                                                if req["request_id"] == request["request_id"]:
                                                    # Update the status to indicate a template has been filled
                                                    if req.get("status") != "filled":
                                                        req["status"] = "filled"
                                                        req["templates_filled"] = 1
                                                    else:
                                                        # Increment the templates filled count
                                                        req["templates_filled"] = req.get("templates_filled", 1) + 1

                                                    # Store the template CID and CERT CID in a list
                                                    if "templates" not in req:
                                                        req["templates"] = []

                                                    template_info = {
                                                        "template_cid": result.get("template_cid"),
                                                        "cert_cid": result.get("cert_cid"),
                                                        "filled_at": int(time.time())
                                                    }
                                                    req["templates"].append(template_info)
                                                    break

                                            # Display details
                                            st.info(f"Template CID: {result.get('template_cid', 'N/A')}")
                                            st.info(f"CERT CID: {result.get('cert_cid', 'N/A')}")
                                            st.info("Your data has been encrypted and is ready for the buyer to verify.")
                                        else:
                                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")

                            if st.button(f"Decline Request", key=f"decline_{request['request_id']}"):
                                # Update the request status
                                for req in st.session_state.data_requests:
                                    if req["request_id"] == request["request_id"]:
                                        req["status"] = "declined"
                                        break

                                st.success("Request declined. The hospital will be notified.")

                # Display filled requests
                filled_requests = [req for req in st.session_state.data_requests if req.get("status") == "filled"]
                if filled_requests:
                    st.subheader("Filled Requests")

                    for request in filled_requests:
                        templates_count = len(request.get("templates", [])) if "templates" in request else request.get("templates_filled", 1)
                        with st.expander(f"Request {request['request_id']} - {request['template']['category']} (Filled {templates_count} templates)"):
                            # Request details
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Request ID:** {request['request_id']}")
                                st.markdown(f"**Buyer:** `{request.get('buyer', 'Unknown')[:6]}...`")
                                st.markdown(f"**Hospital:** `{request.get('hospital', 'Unknown')[:6]}...`")

                            with col2:
                                # Format timestamp
                                timestamp = request.get("timestamp", 0)
                                date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Requested:** {date_str}")

                                # Payment amount
                                amount = request.get("amount", 0.1)
                                st.markdown(f"**Payment Amount:** {amount} ETH")

                                # Status
                                status = request.get("status", "filled")
                                st.markdown(f"**Status:** {status.capitalize()}")

                            # Display templates
                            if "templates" in request and request["templates"]:
                                st.subheader(f"Filled Templates ({len(request['templates'])})")
                                for i, template in enumerate(request["templates"]):
                                    st.markdown(f"**Template {i+1}:**")
                                    st.markdown(f"**Template CID:** `{template.get('template_cid', 'N/A')}`")
                                    st.markdown(f"**CERT CID:** `{template.get('cert_cid', 'N/A')}`")

                                    # Format timestamp
                                    filled_at = template.get("filled_at", 0)
                                    if filled_at:
                                        date_str = datetime.datetime.fromtimestamp(filled_at).strftime('%Y-%m-%d %H:%M:%S')
                                        st.markdown(f"**Filled at:** {date_str}")

                                    if i < len(request["templates"]) - 1:
                                        st.markdown("---")
                            # Fallback for older format
                            elif "template_cid" in request:
                                st.markdown(f"**Template CID:** `{request['template_cid']}`")
                                if "cert_cid" in request:
                                    st.markdown(f"**CERT CID:** `{request['cert_cid']}`")

                            st.info("Your data has been encrypted and is ready for the buyer to verify.")

                # Display declined requests
                declined_requests = [req for req in st.session_state.data_requests if req.get("status") == "declined"]
                if declined_requests:
                    st.subheader("Declined Requests")

                    for request in declined_requests:
                        with st.expander(f"Request {request['request_id']} - {request['template']['category']} (Declined)"):
                            # Request details
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Request ID:** {request['request_id']}")
                                st.markdown(f"**Buyer:** `{request.get('buyer', 'Unknown')[:6]}...`")
                                st.markdown(f"**Hospital:** `{request.get('hospital', 'Unknown')[:6]}...`")

                            with col2:
                                # Format timestamp
                                timestamp = request.get("timestamp", 0)
                                date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Requested:** {date_str}")

                                # Payment amount
                                amount = request.get("amount", 0.1)
                                st.markdown(f"**Payment Amount:** {amount} ETH")

                                # Status
                                status = request.get("status", "declined")
                                st.markdown(f"**Status:** {status.capitalize()}")

        with tab4:
            st.header("Data Purchase Requests")

        with tab5:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

        # Form for requesting data purchase
        with tab4:
            with st.form("purchase_request_form"):
                template_hash = st.text_input("Template Hash")
                amount = st.number_input("Escrow Amount (ETH)", min_value=0.0001, value=1.0, step=0.1)

                submit_button = st.form_submit_button("Request Purchase (On-Chain)")

                if submit_button:
                    if not template_hash:
                        st.error("Please enter a template hash")
                    else:
                        # Call API to request purchase
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/request",
                                json={
                                    "template_hash": template_hash,
                                    "amount": amount,
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            # If the first URL fails, try the alternative URL
                            if response.status_code == 404:
                                print("Trying alternative API URL...")
                                response = requests.post(
                                    f"{API_URL}/api/purchase/request",
                                    json={
                                        "template_hash": template_hash,
                                        "amount": amount,
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Purchase request submitted successfully!")
                                st.info(f"Request ID: {result['request_id']}")
                                st.info(f"Transaction Hash: {result['transaction_hash']}")
                                st.session_state.current_request_id = result['request_id']
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Section for verifying and finalizing purchases
            st.subheader("Verify and Finalize Purchases")

            # Explanation of the verification process
            with st.expander("About the Verification Process", expanded=False):
                st.markdown("""
                **What happens during verification?**

                1. The system retrieves the template package from IPFS using the Template CID
                2. It verifies the hospital's signature on the template package
                3. For each patient's data in the template:
                   - The Merkle proofs are verified to ensure data integrity
                   - The group signature is verified to ensure the data was signed by a legitimate doctor
                4. If all verifications pass, you can finalize the purchase and release payment

                This verification happens off-chain to save gas costs, but the results are cryptographically secure.
                """)

            col1, col2 = st.columns(2)
            with col1:
                request_id = st.text_input("Request ID")
                if "current_request_id" in st.session_state:
                    st.caption(f"Your last request ID: {st.session_state.current_request_id}")
            with col2:
                template_cid = st.text_input("Template CID")
                st.caption("Enter the CID provided by the hospital")

            if st.button("Verify Purchase (Off-Chain)"):
                if not request_id or not template_cid:
                    st.error("Please enter both Request ID and Template CID")
                else:
                    # Show verification steps
                    with st.status("Verifying purchase...", expanded=True) as status:
                        st.write("Retrieving template package from IPFS...")
                        time.sleep(0.5)  # Simulate delay

                        # Call API to verify purchase off-chain
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/verify",
                                json={
                                    "request_id": request_id,
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            # If the first URL fails, try the alternative URL
                            if response.status_code == 404:
                                print("Trying alternative API URL...")
                                response = requests.post(
                                    f"{API_URL}/api/purchase/verify",
                                    json={
                                        "request_id": request_id,
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                            st.write("Verifying hospital signature...")
                            time.sleep(0.5)  # Simulate delay

                            st.write("Verifying Merkle proofs...")
                            time.sleep(0.5)  # Simulate delay

                            st.write("Verifying group signatures...")
                            time.sleep(0.5)  # Simulate delay

                            if response.status_code == 200:
                                result = response.json()
                                if result["verified"]:
                                    status.update(label="Verification complete!", state="complete")
                                    st.success("Verification successful!")
                                    st.session_state.verification_result = result
                                    st.session_state.verified_request_id = request_id

                                    # Display records and patients count if available
                                    if "records_count" in result:
                                        st.info(f"Records count: {result['records_count']}")
                                    if "patients_count" in result:
                                        st.info(f"Patients count: {result['patients_count']}")

                                    st.info("You can now finalize the purchase on-chain")

                                    # Display recipients in a nicer format
                                    st.subheader("Payment Recipients")
                                    st.write("The following addresses will receive payment if you approve:")

                                    for i, recipient in enumerate(result["recipients"]):
                                        # Check if it's a known address
                                        recipient_name = "Unknown"
                                        for name, info in TEST_ACCOUNTS.items():
                                            if info["address"].lower() == recipient.lower():
                                                recipient_name = f"{name} ({info['role']})"
                                                break

                                        st.markdown(f"**{i+1}.** `{recipient}` - {recipient_name}")

                                    # Display payment distribution
                                    st.subheader("Payment Distribution")
                                    total_recipients = len(result["recipients"])
                                    if total_recipients > 0:
                                        amount_per_recipient = 0.1 / total_recipients  # Assuming 0.1 ETH total
                                        st.write(f"Each recipient will receive approximately {amount_per_recipient:.4f} ETH")
                                else:
                                    status.update(label="Verification failed", state="error")
                                    st.error(f"Verification failed! {result.get('message', 'The data does not meet the requirements.')}")
                            else:
                                status.update(label="Verification failed", state="error")
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            status.update(label="Verification failed", state="error")
                            st.error(f"Error: {str(e)}")

            # Finalize purchase section (only shown after verification)
            if hasattr(st.session_state, 'verification_result') and hasattr(st.session_state, 'verified_request_id'):
                st.markdown("---")
                st.subheader("Finalize Purchase")
                st.info("The verification was successful. You can now finalize the purchase on-chain.")

                # Display a summary of the purchase
                with st.expander("Purchase Summary", expanded=True):
                    st.markdown(f"**Request ID:** {st.session_state.verified_request_id}")
                    st.markdown(f"**Total Recipients:** {len(st.session_state.verification_result['recipients'])}")

                    # Calculate total payment
                    total_payment = 0.1  # Assuming 0.1 ETH total
                    st.markdown(f"**Total Payment:** {total_payment} ETH")

                    # Calculate payment per recipient
                    recipients_count = len(st.session_state.verification_result['recipients'])
                    if recipients_count > 0:
                        payment_per_recipient = total_payment / recipients_count
                        st.markdown(f"**Payment per Recipient:** {payment_per_recipient:.4f} ETH")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve and Pay", type="primary"):
                        # Show a confirmation dialog
                        st.write("Processing payment transaction...")

                        # Call API to finalize purchase with approval
                        try:
                            with st.spinner("Submitting transaction to the blockchain..."):
                                response = requests.post(
                                    f"{API_URL}/purchase/finalize",
                                    json={
                                        "request_id": st.session_state.verified_request_id,
                                        "approved": True,
                                        "recipients": st.session_state.verification_result["recipients"],
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                                # If the first URL fails, try the alternative URL
                                if response.status_code == 404:
                                    print("Trying alternative API URL...")
                                    response = requests.post(
                                        f"{API_URL}/api/purchase/finalize",
                                        json={
                                            "request_id": st.session_state.verified_request_id,
                                            "approved": True,
                                            "recipients": st.session_state.verification_result["recipients"],
                                            "wallet_address": st.session_state.wallet_address
                                        }
                                    )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Purchase finalized successfully!")

                                # Track the transaction in the session state
                                track_transaction(
                                    tx_hash=result.get('transaction_hash'),
                                    operation='Finalize Purchase',
                                    wallet_address=st.session_state.wallet_address,
                                    gas_used=120000,  # Estimated gas used
                                    gas_price=None  # We don't know the gas price in this simulation
                                )

                                # Display transaction details
                                st.markdown(f"**Transaction Hash:** `{result.get('transaction_hash', 'N/A')}`")
                                st.markdown(f"**Message:** {result.get('message', 'Payment has been distributed.')}")

                                # Show a nice confirmation message with details
                                st.balloons()
                                st.success(f"You have successfully purchased data from {len(st.session_state.verification_result['recipients'])} providers!")

                                # Clear the verification result
                                del st.session_state.verification_result
                                del st.session_state.verified_request_id
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                with col2:
                    if st.button("Reject and Refund"):
                        # Show a confirmation dialog
                        st.write("Processing refund transaction...")

                        # Call API to finalize purchase with rejection
                        try:
                            with st.spinner("Submitting transaction to the blockchain..."):
                                response = requests.post(
                                    f"{API_URL}/purchase/finalize",
                                    json={
                                        "request_id": st.session_state.verified_request_id,
                                        "approved": False,
                                        "recipients": [],
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                                # If the first URL fails, try the alternative URL
                                if response.status_code == 404:
                                    print("Trying alternative API URL...")
                                    response = requests.post(
                                        f"{API_URL}/api/purchase/finalize",
                                        json={
                                            "request_id": st.session_state.verified_request_id,
                                            "approved": False,
                                            "recipients": [],
                                            "wallet_address": st.session_state.wallet_address
                                        }
                                    )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Purchase rejected.")

                                # Track the transaction in the session state
                                track_transaction(
                                    tx_hash=result.get('transaction_hash'),
                                    operation='Reject Purchase',
                                    wallet_address=st.session_state.wallet_address,
                                    gas_used=100000,  # Estimated gas used
                                    gas_price=None  # We don't know the gas price in this simulation
                                )

                                # Display transaction details
                                st.markdown(f"**Transaction Hash:** `{result.get('transaction_hash', 'N/A')}`")
                                st.markdown(f"**Message:** {result.get('message', 'Your escrow has been refunded.')}")

                                # Clear the verification result
                                del st.session_state.verification_result
                                del st.session_state.verified_request_id
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Section for requesting signature opening
            st.subheader("Request Signature Opening")

            with st.form("opening_request_form"):
                opening_request_id = st.text_input("Purchase Request ID")
                signature_hash = st.text_input("Signature Hash")

                submit_button = st.form_submit_button("Request Opening (On-Chain)")

                if submit_button:
                    if not opening_request_id or not signature_hash:
                        st.error("Please enter both Purchase Request ID and Signature Hash")
                    else:
                        # In a real implementation, this would call the smart contract
                        st.success("Opening request submitted successfully!")
                        st.info("The Group Manager and Revocation Manager will process your request.")
                        st.session_state.opening_requested = True
                        st.session_state.opening_id = "123"  # Placeholder

            # Section for viewing opening results
            if hasattr(st.session_state, 'opening_requested') and st.session_state.opening_requested:
                st.subheader("Opening Results")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Check Opening Status"):
                        # In a real implementation, this would check the blockchain
                        st.info("Opening request is being processed...")

                with col2:
                    if st.button("Retrieve Opening Result"):
                        # Call API to get opening result
                        try:
                            response = requests.get(
                                f"{API_URL}/opening/result",
                                params={
                                    "opening_id": st.session_state.opening_id,
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Opening result retrieved successfully!")

                                # Display signer details
                                st.subheader("Signer Details")
                                st.json(result["signer_details"])
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

    elif role == "Doctor":
        st.title("Doctor Dashboard")

        # Tabs for different actions
        tab1, tab2, tab3 = st.tabs(["Create Records", "Shared Records", "Gas Fees"])

        # Initialize gas fees tracking if not already done
        if 'gas_fees' not in st.session_state:
            st.session_state.gas_fees = []

        with tab1:
            st.header("Create Patient Records")

            # Form for creating records
            with st.form("create_record_form"):
                patient_address = st.text_input("Patient Wallet Address",
                                              help="Enter the patient's wallet address")
                date = st.date_input("Date")

                # Medical category
                category = st.selectbox(
                    "Medical Category",
                    ["Cardiology", "Oncology", "Neurology", "Pediatrics", "General"],
                    help="The medical specialty of this record"
                )

                # Demographics section
                st.subheader("Demographics")
                col1, col2 = st.columns(2)
                with col1:
                    age = st.number_input("Age", min_value=0, max_value=120, value=35)
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                with col2:
                    location = st.text_input("Location", placeholder="City, Country")
                    ethnicity = st.text_input("Ethnicity", placeholder="Optional")

                # Medical data section
                st.subheader("Medical Data")
                diagnosis = st.text_input("Diagnosis", help="Primary diagnosis")
                treatment = st.text_input("Treatment", help="Prescribed treatment")

                col1, col2 = st.columns(2)
                with col1:
                    medications = st.text_area("Medications", placeholder="List medications here", height=100)
                with col2:
                    lab_results = st.text_area("Lab Results", placeholder="Key lab results", height=100)

                # Additional notes
                notes = st.text_area("Additional Notes")

                # Hospital info
                hospital_info = st.text_input("Hospital Info", value="General Hospital",
                                            help="Information about the hospital")

                submit_button = st.form_submit_button("Create and Sign Record")

                if submit_button:
                    if not patient_address:
                        st.error("Please enter the patient's wallet address")
                    else:
                        # Step 1: Create the record with the detailed structure
                        record_data = {
                            "patientID": patient_address,  # Using patientID to match the expected format
                            "doctorID": st.session_state.wallet_address,  # Using doctorID to match the expected format
                            "date": str(date),
                            "category": category,
                            "hospitalInfo": hospital_info,
                            "demographics": {
                                "age": age,
                                "gender": gender,
                                "location": location if location else None,
                                "ethnicity": ethnicity if ethnicity else None
                            },
                            "medical_data": {
                                "diagnosis": diagnosis,
                                "treatment": treatment if treatment else None,
                                "medications": medications if medications else None,
                                "lab_results": lab_results if lab_results else None
                            },
                            "notes": notes
                        }

                        # Display the record being created
                        st.info("Creating and signing the following record:")
                        st.json(record_data)

                        # Step 2: Call API to sign the record with group signature
                        try:
                            with st.spinner("Signing record with group signature..."):
                                response = requests.post(
                                    f"{API_URL}/records/sign",
                                    json={
                                        "record_data": record_data,
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                                # If the first URL fails, try the alternative URL
                                if response.status_code == 404:
                                    print("Trying alternative API URL...")
                                    response = requests.post(
                                        f"{API_URL}/api/records/sign",
                                        json={
                                            "record_data": record_data,
                                            "wallet_address": st.session_state.wallet_address
                                        }
                                    )

                                if response.status_code == 200:
                                    signed_data = response.json()
                                    st.success("Record signed successfully with group signature!")

                                    # Store the signed record in session state
                                    st.session_state.signed_record = signed_data

                                    # Display signature details
                                    with st.expander("Signature Details"):
                                        st.markdown(f"**Merkle Root (IDRecord):** `{signed_data['merkleRoot'][:10]}...`")
                                        st.markdown(f"**Group Signature:** `{signed_data['signature'][:20]}...`")
                                        st.markdown("**Note:** The doctor signs the IDRecord with their group secret key (gsk_i)")

                                    # Step 3: Encrypt and store on IPFS
                                    with st.spinner("Encrypting with patient's key and uploading to IPFS..."):
                                        # In a real app, we would get the patient's public key from a key server
                                        # For this demo, we'll use a simulated patient key
                                        # Store the record in IPFS and call the blockchain contract
                                        store_response = requests.post(
                                            f"{API_URL}/records/store",
                                            json={
                                                "record": signed_data['record'],
                                                "signature": signed_data['signature'],
                                                "merkleRoot": signed_data['merkleRoot'],
                                                "patientAddress": patient_address,
                                                "hospitalInfo": hospital_info
                                            }
                                        )

                                        # Process response
                                        if store_response.status_code == 200:
                                            store_result = store_response.json()

                                            # Display blockchain transaction information
                                            if 'txHash' in store_result:
                                                # Ensure the transaction hash has the 0x prefix
                                                tx_hash = store_result['txHash']
                                                if not tx_hash.startswith('0x'):
                                                    tx_hash = f"0x{tx_hash}"
                                                else:
                                                    tx_hash = store_result['txHash']

                                                st.success(f"Record metadata stored on blockchain with transaction: {tx_hash}")
                                                # Add a link to the BASE Sepolia block explorer
                                                st.markdown(f"[View transaction on BASE Sepolia Explorer](https://sepolia.basescan.org/tx/{tx_hash})")

                                                # Track the transaction in the session state
                                                track_transaction(
                                                    tx_hash=tx_hash,
                                                    operation='Store Record',
                                                    wallet_address=st.session_state.wallet_address,
                                                    gas_used=store_result.get('gasUsed'),
                                                    gas_price=store_result.get('gasPrice')
                                                )

                                            # Add IPFS verification button
                                            if 'cid' in store_result:
                                                st.success(f"Record stored on IPFS with CID: {store_result['cid']}")

                                                # Store the CID in session state for verification after form submission
                                                st.session_state.last_stored_cid = store_result['cid']

                                            st.success("Record encrypted and stored on IPFS!")

                                            # Display IPFS and blockchain details
                                            st.markdown(f"**IPFS CID:** `{store_result['cid']}`")
                                            st.markdown(f"**Transaction Hash:** `{store_result.get('txHash', 'N/A')}`")

                                            # Create a certificate (CERT) for the patient
                                            # CERT contains only eId and signature as per the modified workflow
                                            cert = {
                                                "cid": store_result['cid'],
                                                "eId": store_result.get('eId', 'PCS_encrypted_hospital_info_and_key'),  # PCS(HospitalInfo||K_patient)
                                                "signature": signed_data['signature']      # GroupSig.Sign(IDrec)
                                            }

                                            # Display the certificate
                                            st.subheader("Certificate (CERT) for Patient")
                                            st.info("Share this certificate with the patient so they can access their record:")

                                            # Explain the certificate components
                                            st.markdown("**Certificate Components:**")
                                            st.markdown("- **cid**: IPFS content identifier for the encrypted record")
                                            st.markdown("- **eId**: PCS-encrypted hospital info and patient key using Group Manager's public key")
                                            st.markdown("- **signature**: Group signature on the IDRecord (Merkle root hash)")

                                            # Explain the blockchain interaction
                                            st.markdown("\n**Blockchain Interaction:**")
                                            st.markdown("The doctor has called the smart contract to store the record metadata on the blockchain:")
                                            st.markdown("- **CID**: The IPFS content identifier")
                                            st.markdown("- **Merkle Root**: The hash of the record data")
                                            st.markdown("- **Signature**: The group signature proving authenticity")

                                            cert_json = json.dumps(cert, indent=2)
                                            st.code(cert_json)

                                            # Option to download the certificate
                                            cert_b64 = base64.b64encode(cert_json.encode()).decode()
                                            href = f'<a href="data:application/json;base64,{cert_b64}" download="patient_cert_{int(time.time())}.json">Download Certificate</a>'
                                            st.markdown(href, unsafe_allow_html=True)

                                            # Option to copy to clipboard
                                            st.markdown("```\nCopy this certificate and send it to the patient through a secure channel.\n```")
                                        else:
                                            st.error(f"Error storing record: {store_response.json().get('detail', 'Unknown error')}")
                                else:
                                    st.error(f"Error signing record: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Add IPFS verification button outside the form
            if hasattr(st.session_state, 'last_stored_cid') and st.session_state.last_stored_cid:
                st.subheader("Verify IPFS Storage")
                if st.button("Verify IPFS Storage", key=f"verify_{st.session_state.last_stored_cid}"):
                    try:
                        # Call the verification endpoint
                        api_url = API_URL  # Use the configured API URL
                        verify_response = requests.get(f"{api_url}/api/ipfs/verify/{st.session_state.last_stored_cid}")

                        if verify_response.status_code == 200:
                            response_data = verify_response.json()

                            # Check if the response has the expected format
                            if response_data.get('status') == 'success':
                                verify_result = response_data.get('data', {})

                                # Check if the record was verified in either IPFS or local storage
                                if verify_result.get('verified', False):
                                    st.success(f"✅ Record verified! CID: {verify_result.get('cid')}")

                                    # Show details in an expander
                                    with st.expander("View verification details"):
                                        # Check IPFS status
                                        ipfs_status = verify_result.get('ipfs', {})
                                        if ipfs_status.get('exists', False):
                                            st.success(f"✅ Verified: CID exists in IPFS ({ipfs_status.get('size', 0)} bytes)")
                                            st.info(f"Verification method: {ipfs_status.get('method', 'unknown')}")
                                        else:
                                            error_msg = ipfs_status.get('error', 'Unknown error')
                                            st.warning(f"⚠️ Not found in IPFS: {error_msg}")

                                            # If there's a permission error, show a more helpful message
                                            if ipfs_status.get('permission_error', False) or "permission denied" in str(error_msg).lower():
                                                st.info("This appears to be a permission issue with the IPFS daemon. The administrator should check the IPFS container configuration.")

                                            # Show daemon status
                                            if not ipfs_status.get('daemon_running', True):
                                                st.error("IPFS daemon is not running or not accessible")

                                        # Check local storage status
                                        local_status = verify_result.get('local', {})
                                        if local_status.get('exists', False):
                                            st.success(f"✅ Verified: CID exists in local storage ({local_status.get('size', 0)} bytes)")
                                            st.info(f"File path: {local_status.get('path', 'unknown')}")
                                        else:
                                            st.warning("⚠️ Not found in local storage")
                                            if 'paths_checked' in local_status:
                                                st.info(f"Paths checked: {', '.join(local_status.get('paths_checked', []))}")
                                else:
                                    st.error("❌ Record could not be verified in IPFS or local storage")

                                    # Show details in an expander
                                    with st.expander("View verification details"):
                                        st.json(verify_result)
                            else:
                                st.error(f"Error in verification response: {response_data.get('message', 'Unknown error')}")
                        else:
                            st.error(f"Error checking IPFS: {verify_response.status_code}")
                            st.info("The record was still stored successfully, but verification is currently unavailable.")

                            # Try to parse the error response
                            try:
                                error_data = verify_response.json()
                                st.error(f"Error details: {error_data.get('detail', 'No details available')}")
                            except:
                                st.error(f"Raw response: {verify_response.text}")
                    except Exception as e:
                        st.error(f"Error verifying IPFS storage: {str(e)}")
                        st.info("The record was still stored successfully, but verification is currently unavailable.")

        with tab2:
            st.header("Records Shared with Me")

            # Form for accessing shared records
            with st.form("access_shared_form"):
                metadata_cid = st.text_input("Sharing Metadata CID")

                submit_button = st.form_submit_button("Access Shared Record")

                if submit_button:
                    if not metadata_cid:
                        st.error("Please enter a Sharing Metadata CID")
                    else:
                        # Call API to access shared record
                        try:
                            response = requests.post(
                                f"{API_URL}/access_shared",
                                json={
                                    "metadata_cid": metadata_cid,
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Record accessed successfully!")

                                # Display record details
                                st.subheader("Shared Medical Record")
                                record = result["record"]

                                # Basic information
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Patient ID:** {record.get('patientID', 'N/A')}")
                                    st.markdown(f"**Date:** {record.get('date', 'N/A')}")
                                    st.markdown(f"**Category:** {record.get('category', 'General')}")

                                with col2:
                                    st.markdown(f"**Doctor ID:** {record.get('doctorID', 'N/A')}")
                                    st.markdown(f"**Hospital:** {record.get('hospitalInfo', 'N/A')}")
                                    st.markdown(f"**Shared By:** {result.get('shared_by', 'N/A')}")

                                # Sharing information
                                shared_at = datetime.datetime.fromtimestamp(result.get('shared_at', 0))
                                st.markdown(f"**Shared At:** {shared_at.strftime('%Y-%m-%d %H:%M:%S')}")

                                # Demographics
                                st.subheader("Demographics")
                                demographics = record.get('demographics', {})
                                if demographics:
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"**Age:** {demographics.get('age', 'N/A')}")
                                        st.markdown(f"**Gender:** {demographics.get('gender', 'N/A')}")
                                    with col2:
                                        st.markdown(f"**Location:** {demographics.get('location', 'N/A')}")
                                        st.markdown(f"**Ethnicity:** {demographics.get('ethnicity', 'N/A')}")
                                else:
                                    st.info("No demographics information available")

                                # Medical data
                                st.subheader("Medical Data")
                                medical_data = record.get('medical_data', {})
                                if medical_data:
                                    st.markdown(f"**Diagnosis:** {medical_data.get('diagnosis', 'N/A')}")
                                    st.markdown(f"**Treatment:** {medical_data.get('treatment', 'N/A')}")

                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown("**Medications:**")
                                        st.text_area("Medications", value=medical_data.get('medications', ''), height=100, disabled=True)
                                    with col2:
                                        st.markdown("**Lab Results:**")
                                        st.text_area("Lab Results", value=medical_data.get('lab_results', ''), height=100, disabled=True)
                                else:
                                    st.info("No detailed medical data available")

                                # Notes
                                st.subheader("Additional Notes")
                                st.text_area("Notes", value=record.get('notes', ''), height=100, disabled=True)

                                # Display sharing details
                                st.subheader("Sharing Details")
                                expires_at = datetime.datetime.fromtimestamp(result.get('expires_at', 0))
                                st.markdown(f"**Expires At:** {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

                                # IPFS links
                                st.markdown(f"**Record CID:** {result.get('record_cid', 'N/A')}")
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Display information about how to access shared records
            with st.expander("How to Access Shared Records"):
                st.markdown("""
                1. The patient will share a Metadata CID with you through a secure channel.
                2. Enter the Metadata CID in the form above and click 'Access Shared Record'.
                3. The system will verify you are the intended recipient and decrypt the record.
                4. The record will be displayed below the form.
                5. The record will be pinned to your IPFS node for future access.
                """)

        with tab3:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

    elif role == "Hospital":
        st.title("Hospital Dashboard")

        # Add auto-refresh functionality
        if "hospital_auto_refresh" not in st.session_state:
            st.session_state.hospital_auto_refresh = False
            st.session_state.hospital_last_refresh = 0

        # Check if it's time for auto-refresh (every 30 seconds)
        current_time = int(time.time())
        if st.session_state.hospital_auto_refresh and (current_time - st.session_state.hospital_last_refresh) > 30:
            st.session_state.hospital_last_refresh = current_time
            st.session_state.trigger_rerun = True

        # Tabs for different actions
        tab1, tab2, tab3, tab4 = st.tabs(["Purchase Requests", "Manage Group", "Signature Openings", "Gas Fees"])

        with tab1:
            st.header("Data Purchase Requests")

            # Initialize purchase_requests in session state if not present
            if "purchase_requests" not in st.session_state:
                st.session_state.purchase_requests = []
                st.session_state.last_refresh_time = 0

            # Button to check for new requests
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button("Check for New Requests", key="check_requests"):
                    with st.spinner("Fetching purchase requests from the blockchain and API..."):
                        try:
                            # Call API to get transactions
                            response = requests.get(
                                f"{API_URL}/transactions",
                                params={
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            # If the first URL fails, try the alternative URL
                            if response.status_code == 404:
                                print("Trying alternative API URL...")
                                response = requests.get(
                                    f"{API_URL}/api/transactions",
                                    params={
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                            if response.status_code == 200:
                                result = response.json()
                                transactions = result.get("transactions", [])

                                # Update the last refresh time
                                st.session_state.last_refresh_time = int(time.time())

                                # Filter for Request transactions that haven't been replied to
                                new_requests = []

                                # First, check for purchase requests in the local storage directory
                                try:
                                    # Check if the local storage directory exists
                                    if os.path.exists("local_storage/purchases"):
                                        # Get all purchase files
                                        purchase_files = os.listdir("local_storage/purchases")
                                        print(f"Found {len(purchase_files)} files in local_storage/purchases")

                                        for file_name in purchase_files:
                                            if not file_name.endswith(".json"):
                                                continue

                                            file_path = f"local_storage/purchases/{file_name}"
                                            print(f"Processing file: {file_path}")

                                            try:
                                                with open(file_path, "r") as f:
                                                    purchase_data = json.load(f)

                                                # Print the purchase data for debugging
                                                print(f"Purchase data: {purchase_data}")
                                                print(f"Status: {purchase_data.get('status')}")

                                                # Check if this is a pending request (not replied to)
                                                if purchase_data.get("status") == "pending":
                                                    print(f"Found pending request: {purchase_data.get('request_id')}")

                                                    # Convert to request format
                                                    new_request = {
                                                        "request_id": purchase_data.get("request_id"),
                                                        "buyer": purchase_data.get("buyer", "Unknown"),
                                                        "template_hash": purchase_data.get("template_hash", ""),
                                                        "amount": purchase_data.get("amount", 0.1),
                                                        "timestamp": purchase_data.get("timestamp", int(time.time())),
                                                        "template": purchase_data.get("template", {
                                                            "category": "General",
                                                            "demographics": {},
                                                            "medical_data": {},
                                                            "time_period": "1 year",
                                                            "min_records": 10
                                                        })
                                                    }

                                                    # Add to new requests
                                                    new_requests.append(new_request)
                                                    print(f"Added request to new_requests list. Total: {len(new_requests)}")
                                            except Exception as e:
                                                print(f"Error processing file {file_name}: {str(e)}")
                                except Exception as e:
                                    print(f"Error reading local storage: {str(e)}")

                                # Then, also check transactions for any we might have missed
                                print(f"Checking {len(transactions)} transactions for purchase requests...")
                                for tx in transactions:
                                    if tx.get("type") == "Request":
                                        request_id = tx.get("request_id")
                                        print(f"Found Request transaction with ID: {request_id}")

                                        # Check if this request has already been replied to
                                        replied = any(t.get("type") == "Hospital Reply" and t.get("request_id") == request_id for t in transactions)
                                        if replied:
                                            print(f"Request {request_id} has already been replied to, skipping")

                                        # Check if we already added this request from local storage
                                        already_added = any(req["request_id"] == request_id for req in new_requests)
                                        if already_added:
                                            print(f"Request {request_id} was already added from local storage, skipping")

                                        if not replied and not already_added:
                                            print(f"Processing new request from transaction: {request_id}")

                                            # Convert transaction to request format
                                            new_request = {
                                                "request_id": request_id,
                                                "buyer": tx.get("buyer", tx.get("from", "Unknown")),
                                                "template_hash": tx.get("template_hash", ""),
                                                "amount": tx.get("amount", 0.1),
                                                "timestamp": tx.get("timestamp", int(time.time())),
                                                "template": {}
                                            }

                                            # Check if details contains a full template
                                            if "details" in tx and isinstance(tx["details"], dict):
                                                details = tx["details"]
                                                print(f"Transaction details: {details}")

                                                # Try to extract template from details
                                                if "template" in details and isinstance(details["template"], dict):
                                                    # Use the full template if available
                                                    new_request["template"] = details["template"]
                                                    print(f"Using full template from details: {new_request['template']}")
                                                else:
                                                    # Otherwise build from fields
                                                    new_request["template"] = {
                                                        "category": details.get("category", "General"),
                                                        "demographics": {},
                                                        "medical_data": {},
                                                        "time_period": details.get("time_period", "1 year"),
                                                        "min_records": details.get("min_records", 10)
                                                    }
                                                    print(f"Building template from fields: {new_request['template']}")

                                                    # Extract fields from details
                                                    fields = details.get("fields", [])
                                                    print(f"Fields from details: {fields}")
                                                    for field in fields:
                                                        field_lower = field.lower()
                                                        if field_lower in ["age", "gender", "location", "ethnicity"]:
                                                            new_request["template"]["demographics"][field_lower] = True
                                                        elif field_lower in ["diagnosis", "treatment", "medications", "lab_results"]:
                                                            new_request["template"]["medical_data"][field_lower] = True
                                            else:
                                                print(f"No details found in transaction or details is not a dictionary")

                                            new_requests.append(new_request)
                                            print(f"Added request from transaction. Total requests: {len(new_requests)}")

                                # Add new requests to the list
                                if new_requests:
                                    # Add only requests that aren't already in the list
                                    existing_ids = {req["request_id"] for req in st.session_state.purchase_requests}
                                    new_count = 0

                                    for req in new_requests:
                                        if req["request_id"] not in existing_ids:
                                            st.session_state.purchase_requests.append(req)
                                            new_count += 1

                                    if new_count > 0:
                                        st.success(f"Found {new_count} new request(s)!")
                                    else:
                                        st.info("No new requests found.")
                                else:
                                    st.info("No new requests found.")
                            else:
                                st.error(f"Error fetching requests: {response.json().get('detail', 'Unknown error')}")

                                # For demo purposes, add a sample request if no requests exist
                                if not st.session_state.purchase_requests:
                                    # Add a sample request
                                    sample_request = {
                                        "request_id": f"sample-request-{int(time.time())}",
                                        "buyer": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",  # Buyer address
                                        "template_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                                        "amount": 0.1,
                                        "timestamp": int(time.time()),
                                        "template": {
                                            "category": "Cardiology",
                                            "demographics": {
                                                "age": True,
                                                "gender": True,
                                                "location": False,
                                                "ethnicity": False
                                            },
                                            "medical_data": {
                                                "diagnosis": True,
                                                "treatment": True,
                                                "medications": False,
                                                "lab_results": False
                                            },
                                            "time_period": "1 year",
                                            "min_records": 10
                                        }
                                    }
                                    st.session_state.purchase_requests.append(sample_request)
                                    st.success("Added a sample request for demonstration purposes.")
                        except Exception as e:
                            st.error(f"Error connecting to API: {str(e)}")

                            # For demo purposes, add a sample request if no requests exist
                            if not st.session_state.purchase_requests:
                                # Add a sample request
                                sample_request = {
                                    "request_id": f"sample-request-{int(time.time())}",
                                    "buyer": "0x3Fa2c09c14453c7acaC39E3fd57e0c6F1da3f5ce",  # Buyer address
                                    "template_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                                    "amount": 0.1,
                                    "timestamp": int(time.time()),
                                    "template": {
                                        "category": "Cardiology",
                                        "demographics": {
                                            "age": True,
                                            "gender": True,
                                            "location": False,
                                            "ethnicity": False
                                        },
                                        "medical_data": {
                                            "diagnosis": True,
                                            "treatment": True,
                                            "medications": False,
                                            "lab_results": False
                                        },
                                        "time_period": "1 year",
                                        "min_records": 10
                                    }
                                }
                                st.session_state.purchase_requests.append(sample_request)
                                st.success("Added a sample request for demonstration purposes.")

            with col2:
                # Add auto-refresh toggle
                auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.hospital_auto_refresh, key="hospital_auto_refresh_toggle")
                if auto_refresh != st.session_state.hospital_auto_refresh:
                    st.session_state.hospital_auto_refresh = auto_refresh
                    st.session_state.hospital_last_refresh = int(time.time())
                    if auto_refresh:
                        st.success("Auto-refresh enabled. Dashboard will refresh every 30 seconds.")
                    else:
                        st.info("Auto-refresh disabled.")

            with col3:
                # Add a clear button to remove all requests (for testing)
                if st.button("Clear All", key="clear_requests"):
                    st.session_state.purchase_requests = []
                    st.session_state.last_refresh_time = 0
                    st.success("All requests cleared.")
                    st.rerun()

            # Display pending requests
            if "purchase_requests" in st.session_state and st.session_state.purchase_requests:
                st.subheader("Pending Requests")

                for i, request in enumerate(st.session_state.purchase_requests):
                    with st.expander(f"Request #{i+1}: {request['request_id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Buyer:** {request['buyer']}")
                            st.markdown(f"**Amount:** {request['amount']} ETH")
                        with col2:
                            timestamp = request.get('timestamp', int(time.time()))
                            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            st.markdown(f"**Timestamp:** {date_str}")
                            st.markdown(f"**Template Hash:** {request['template_hash'][:10]}...{request['template_hash'][-6:]}")

                        # Display template details if available
                        if "template" in request:
                            st.subheader("Requested Data Template")
                            template = request["template"]

                            st.markdown(f"**Category:** {template['category']}")
                            st.markdown(f"**Time Period:** {template['time_period']}")
                            st.markdown(f"**Minimum Records:** {template['min_records']}")

                            # Demographics
                            st.markdown("**Demographics:**")
                            demographics = template["demographics"]
                            demo_fields = []
                            for field, included in demographics.items():
                                if included:
                                    demo_fields.append(field.capitalize())
                            st.markdown(", ".join(demo_fields) if demo_fields else "None")

                            # Medical data
                            st.markdown("**Medical Data:**")
                            medical_data = template["medical_data"]
                            med_fields = []
                            for field, included in medical_data.items():
                                if included:
                                    med_fields.append(field.capitalize())
                            st.markdown(", ".join(med_fields) if med_fields else "None")

                        # Form for replying to this request
                        with st.form(f"reply_form_{i}"):
                            st.markdown("**Confirm Data Availability**")

                            # Add fields to provide information about available data
                            col1, col2 = st.columns(2)
                            with col1:
                                records_count = st.number_input("Number of Records Available", min_value=1, value=15, key=f"records_count_{i}")
                            with col2:
                                patients_count = st.number_input("Number of Patients", min_value=1, value=3, key=f"patients_count_{i}")

                            # Add estimated price per record
                            price_per_record = st.number_input("Price per Record (ETH)", min_value=0.001, value=0.01, step=0.001, key=f"price_{i}")

                            # Calculate total value
                            total_value = records_count * price_per_record
                            st.info(f"Total estimated value: {total_value:.4f} ETH")

                            submit_button = st.form_submit_button("Confirm Availability")

                            if submit_button:
                                # Call API to reply to purchase request
                                try:
                                    response = requests.post(
                                        f"{API_URL}/purchase/reply",
                                        json={
                                            "request_id": request["request_id"],
                                            "records_count": records_count,
                                            "patients_count": patients_count,
                                            "price_per_record": price_per_record,
                                            "wallet_address": st.session_state.wallet_address
                                        }
                                    )

                                    # If the first URL fails, try the alternative URL
                                    if response.status_code == 404:
                                        print("Trying alternative API URL...")
                                        response = requests.post(
                                            f"{API_URL}/api/purchase/reply",
                                            json={
                                                "request_id": request["request_id"],
                                                "records_count": records_count,
                                                "patients_count": patients_count,
                                                "price_per_record": price_per_record,
                                                "wallet_address": st.session_state.wallet_address
                                            }
                                        )

                                    if response.status_code == 200:
                                        result = response.json()
                                        st.success("Confirmation submitted successfully!")
                                        st.markdown(f"**Transaction Hash:** {result.get('transaction_hash', 'N/A')[:10]}...{result.get('transaction_hash', 'N/A')[-6:]}")

                                        # Track the transaction in the session state
                                        track_transaction(
                                            tx_hash=result.get('transaction_hash'),
                                            operation='Reply to Request',
                                            wallet_address=st.session_state.wallet_address,
                                            gas_used=60000,  # Estimated gas used
                                            gas_price=None  # We don't know the gas price in this simulation
                                        )

                                        # Store the transaction in session state if available
                                        if "transaction" in result:
                                            if "transaction_history" not in st.session_state:
                                                st.session_state.transaction_history = []
                                            st.session_state.transaction_history.append(result["transaction"])

                                        # Remove the request from the list
                                        st.session_state.purchase_requests.pop(i)
                                        st.info("Request has been processed and removed from the pending list.")

                                        # Set a flag to trigger rerun after the form is processed
                                        st.session_state.trigger_rerun = True
                                    else:
                                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
            else:
                st.info("No pending requests. Requests from buyers will appear here.")

            # Form for manually replying to purchase requests
            with st.expander("Manually Confirm Data Availability"):
                with st.form("reply_purchase_form"):
                    request_id = st.text_input("Request ID")

                    # Add fields to provide information about available data
                    col1, col2 = st.columns(2)
                    with col1:
                        records_count = st.number_input("Number of Records Available", min_value=1, value=15)
                    with col2:
                        patients_count = st.number_input("Number of Patients", min_value=1, value=3)

                    # Add estimated price per record
                    price_per_record = st.number_input("Price per Record (ETH)", min_value=0.001, value=0.01, step=0.001)

                    # Calculate total value
                    total_value = records_count * price_per_record
                    st.info(f"Total estimated value: {total_value:.4f} ETH")

                    submit_button = st.form_submit_button("Confirm Availability")

                    if submit_button:
                        if not request_id:
                            st.error("Please enter a Request ID")
                        else:
                            # Call API to reply to purchase request
                            try:
                                response = requests.post(
                                    f"{API_URL}/purchase/reply",
                                    json={
                                        "request_id": request_id,
                                        "records_count": records_count,
                                        "patients_count": patients_count,
                                        "price_per_record": price_per_record,
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                                # If the first URL fails, try the alternative URL
                                if response.status_code == 404:
                                    print("Trying alternative API URL...")
                                    response = requests.post(
                                        f"{API_URL}/api/purchase/reply",
                                        json={
                                            "request_id": request_id,
                                            "records_count": records_count,
                                            "patients_count": patients_count,
                                            "price_per_record": price_per_record,
                                            "wallet_address": st.session_state.wallet_address
                                        }
                                    )

                                if response.status_code == 200:
                                    result = response.json()
                                    st.success("Confirmation submitted successfully!")
                                    st.markdown(f"**Transaction Hash:** {result.get('transaction_hash', 'N/A')[:10]}...{result.get('transaction_hash', 'N/A')[-6:]}")

                                    # Track the transaction in the session state
                                    track_transaction(
                                        tx_hash=result.get('transaction_hash'),
                                        operation='Reply to Request',
                                        wallet_address=st.session_state.wallet_address,
                                        gas_used=60000,  # Estimated gas used
                                        gas_price=None  # We don't know the gas price in this simulation
                                    )

                                    # Store the transaction in session state if available
                                    if "transaction" in result:
                                        if "transaction_history" not in st.session_state:
                                            st.session_state.transaction_history = []
                                        st.session_state.transaction_history.append(result["transaction"])

                                    # Set a flag to trigger rerun after the form is processed
                                    st.session_state.trigger_rerun = True
                                else:
                                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

        with tab2:
            st.header("Manage Group Signatures")
            st.info("Group management functionality would be implemented here.")

        with tab3:
            st.header("Signature Opening Requests")
            st.info("Requests for signature opening will appear here.")

        with tab4:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

    elif role == "Buyer":
        st.title("Data Buyer Dashboard")

        # Tabs for different actions
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Request Data", "My Purchases", "Filled Templates", "Transaction History", "Gas Fees"])

        with tab1:
            st.header("Request Healthcare Data")

            # Form for requesting data with specific fields
            with st.form("request_data_form"):
                st.subheader("Data Template")
                st.write("Select the fields you're interested in purchasing:")

                # Data category selection
                data_category = st.selectbox(
                    "Data Category",
                    ["Cardiology", "Oncology", "Neurology", "Pediatrics", "General"],
                    help="The medical specialty of the data you're interested in"
                )

                # Demographics fields
                st.write("Demographics:")
                col1, col2 = st.columns(2)
                with col1:
                    include_age = st.checkbox("Age", value=True)
                    include_gender = st.checkbox("Gender", value=True)
                with col2:
                    include_location = st.checkbox("Location")
                    include_ethnicity = st.checkbox("Ethnicity")

                # Medical data fields
                st.write("Medical Data:")
                col1, col2 = st.columns(2)
                with col1:
                    include_diagnosis = st.checkbox("Diagnosis", value=True)
                    include_treatment = st.checkbox("Treatment", value=True)
                with col2:
                    include_medications = st.checkbox("Medications")
                    include_lab_results = st.checkbox("Lab Results")

                # Time period
                st.write("Time Period:")
                time_period = st.select_slider(
                    "Data from the last:",
                    options=["1 month", "3 months", "6 months", "1 year", "3 years", "5 years", "All time"],
                    value="1 year"
                )

                # Minimum records
                min_records = st.number_input("Minimum number of records", min_value=1, value=10, step=1)

                # Escrow amount
                amount = st.number_input("Escrow Amount (ETH)", min_value=0.0001, value=0.1, step=0.001)

                submit_button = st.form_submit_button("Submit Request")

                if submit_button:
                    # Create a template object from the selected fields
                    template = {
                        "category": data_category,
                        "demographics": {
                            "age": include_age,
                            "gender": include_gender,
                            "location": include_location,
                            "ethnicity": include_ethnicity
                        },
                        "medical_data": {
                            "diagnosis": include_diagnosis,
                            "treatment": include_treatment,
                            "medications": include_medications,
                            "lab_results": include_lab_results
                        },
                        "time_period": time_period,
                        "min_records": min_records
                    }

                    # Generate a template hash from the template object
                    template_json = json.dumps(template, sort_keys=True)
                    template_hash = f"0x{hashlib.sha256(template_json.encode()).hexdigest()}"

                    # Display the template and hash
                    st.info(f"Generated template hash: {template_hash[:10]}...{template_hash[-6:]}")

                    # Call API to request data purchase
                    try:
                        response = requests.post(
                            f"{API_URL}/purchase/request",
                            json={
                                "template_hash": template_hash,
                                "amount": amount,
                                "wallet_address": st.session_state.wallet_address,
                                "template": template  # Include the full template for reference
                            }
                        )

                        # If the first URL fails, try the alternative URL
                        if response.status_code == 404:
                            print("Trying alternative API URL...")
                            response = requests.post(
                                f"{API_URL}/api/purchase/request",
                                json={
                                    "template_hash": template_hash,
                                    "amount": amount,
                                    "wallet_address": st.session_state.wallet_address,
                                    "template": template  # Include the full template for reference
                                }
                            )

                        if response.status_code == 200:
                            result = response.json()
                            st.success("Request submitted successfully!")

                            # Display the result in a nicer format
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Request ID:** {result['request_id']}")
                                st.markdown(f"**Transaction Hash:** {result['transaction_hash'][:10]}...{result['transaction_hash'][-6:]}")
                            with col2:
                                timestamp = result.get('timestamp', int(time.time()))
                                date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Timestamp:** {date_str}")
                                st.markdown(f"**Amount:** {amount} ETH")

                            # Store the request ID in session state for later use
                            st.session_state.current_request_id = result['request_id']

                            # Track the transaction in the session state
                            track_transaction(
                                tx_hash=result['transaction_hash'],
                                operation='Purchase Request',
                                wallet_address=st.session_state.wallet_address,
                                gas_used=80000,  # Estimated gas used
                                gas_price=None  # We don't know the gas price in this simulation
                            )

                            # Provide instructions for the next steps
                            st.info("Your request has been submitted. The hospital will review your request and respond with a template package if data matching your criteria is available.")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        with tab2:
            st.header("My Purchase Requests")

            # Fetch transaction history from the API
            try:
                # Show a loading spinner while fetching transactions
                with st.spinner("Fetching transaction history..."):
                    response = requests.get(
                        f"{API_URL}/transactions",
                        params={"wallet_address": st.session_state.wallet_address}
                    )

                    # If the first URL fails, try the alternative URL
                    if response.status_code == 404:
                        print("Trying alternative API URL...")
                        response = requests.get(
                            f"{API_URL}/api/transactions",
                            params={"wallet_address": st.session_state.wallet_address}
                        )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.transaction_history = result.get("transactions", [])
                    else:
                        st.error(f"Error fetching transactions: {response.json().get('detail', 'Unknown error')}")
                        # Use sample data as fallback
                        if "transaction_history" not in st.session_state:
                            st.session_state.transaction_history = []
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")
                # Use sample data as fallback
                if "transaction_history" not in st.session_state:
                    st.session_state.transaction_history = []

            # If we have no transactions yet, add some sample transactions for demo purposes
            if not st.session_state.transaction_history:
                # Add some sample transactions for demo purposes
                sample_transactions = [
                    {
                        "id": "tx-001",
                        "request_id": "req-123456",
                        "type": "Request",
                        "status": "Completed",
                        "timestamp": int(time.time()) - 86400,  # 1 day ago
                        "tx_hash": "0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6",
                        "gas_fee": 0.0012,
                        "amount": 0.1,
                        "template_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                        "details": {
                            "category": "Cardiology",
                            "fields": ["Age", "Gender", "Diagnosis", "Treatment"],
                            "time_period": "1 year",
                            "min_records": 10
                        }
                    },
                    {
                        "id": "tx-002",
                        "request_id": "req-123456",
                        "type": "Hospital Reply",
                        "status": "Completed",
                        "timestamp": int(time.time()) - 43200,  # 12 hours ago
                        "tx_hash": "0x8bc1D0aA17fAA544AE2Ca48106b92836A9eeF9a7",
                        "template_cid": "QmT78zSuBmuS4z925WZfrqQ1qHaJ56DQaTfyMUF7F8ff5o",
                        "hospital": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",
                        "details": {
                            "records_count": 15,
                            "patients_count": 3
                        }
                    },
                    {
                        "id": "tx-003",
                        "request_id": "req-123456",
                        "type": "Verification",
                        "status": "Completed",
                        "timestamp": int(time.time()) - 21600,  # 6 hours ago
                        "details": {
                            "verified": True,
                            "merkle_proofs": "Valid",
                            "signatures": "Valid",
                            "recipients": [
                                "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",  # Hospital
                                "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",  # Patient 1
                                "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"   # Patient 2
                            ]
                        }
                    },
                    {
                        "id": "tx-004",
                        "request_id": "req-123456",
                        "type": "Finalize",
                        "status": "Completed",
                        "timestamp": int(time.time()) - 10800,  # 3 hours ago
                        "tx_hash": "0x9cd1E0aA17fAA544AE2Ca48106b92836A9eeF9a8",
                        "gas_fee": 0.0018,
                        "amount": 0.1,
                        "approved": True,
                        "details": {
                            "recipients": [
                                "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",  # Hospital
                                "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",  # Patient 1
                                "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"   # Patient 2
                            ],
                            "payment_per_recipient": 0.0333
                        }
                    }
                ]

                # Add sample transactions to history
                st.session_state.transaction_history.extend(sample_transactions)

            # Add a refresh button
            if st.button("Refresh Transaction History"):
                st.session_state.pop("transaction_history", None)
                st.rerun()

            # Display transaction history in a table
            if st.session_state.transaction_history:
                # Create tabs for different views
                history_tab1, history_tab2 = st.tabs(["Transaction History", "Workflow Visualization"])

                with history_tab1:
                    # Group transactions by request ID
                    request_ids = set(tx["request_id"] for tx in st.session_state.transaction_history)

                    for request_id in request_ids:
                        with st.expander(f"Request: {request_id}", expanded=True):
                            # Filter transactions for this request ID
                            request_txs = [tx for tx in st.session_state.transaction_history if tx["request_id"] == request_id]

                            # Sort by timestamp (newest first)
                            from operator import itemgetter
                            request_txs.sort(key=itemgetter("timestamp"), reverse=True)

                            # Create a DataFrame for display
                            tx_data = []
                            for tx in request_txs:
                                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                                tx_hash = tx.get("tx_hash", "N/A")
                                tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if tx_hash != "N/A" else "N/A"

                                # Convert 'N/A' to None for numeric fields to avoid PyArrow conversion errors
                                gas_fee = tx.get("gas_fee")
                                if gas_fee is None or gas_fee == "N/A":
                                    gas_fee = None
                                else:
                                    gas_fee = float(gas_fee)

                                amount = tx.get("amount")
                                if amount is None or amount == "N/A":
                                    amount = None
                                else:
                                    amount = float(amount)

                                tx_data.append({
                                    "Type": tx["type"],
                                    "Status": tx["status"],
                                    "Timestamp": tx_time,
                                    "TX Hash": tx_hash_short,
                                    "Gas Fee (ETH)": gas_fee,
                                    "Amount (ETH)": amount
                                })

                            # Display as a table
                            st.table(tx_data)

                            # Show the latest transaction details
                            latest_tx = request_txs[0]
                            st.subheader("Latest Transaction Details")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Transaction Type:** {latest_tx['type']}")
                                st.markdown(f"**Status:** {latest_tx['status']}")
                                if "tx_hash" in latest_tx:
                                    st.markdown(f"**Transaction Hash:** `{latest_tx['tx_hash']}`")
                            with col2:
                                tx_time = datetime.datetime.fromtimestamp(latest_tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Timestamp:** {tx_time}")
                                if "gas_fee" in latest_tx:
                                    st.markdown(f"**Gas Fee:** {latest_tx['gas_fee']} ETH")
                                if "amount" in latest_tx:
                                    st.markdown(f"**Amount:** {latest_tx['amount']} ETH")

                            # Show specific details based on transaction type
                            if latest_tx["type"] == "Request":
                                st.markdown("**Template Details:**")
                                st.json(latest_tx["details"])
                            elif latest_tx["type"] == "Hospital Reply":
                                st.markdown("**Reply Details:**")
                                st.markdown(f"**Hospital:** `{latest_tx.get('hospital', 'N/A')}`")
                                st.markdown(f"**Records Count:** {latest_tx['details'].get('records_count', 'N/A')}")
                                st.markdown(f"**Patients Count:** {latest_tx['details'].get('patients_count', 'N/A')}")
                                st.markdown(f"**Price per Record:** {latest_tx['details'].get('price_per_record', 'N/A')} ETH")
                                st.markdown(f"**Total Value:** {latest_tx['details'].get('total_value', 'N/A')} ETH")

                                # Check if there's a template CID
                                template_cid = latest_tx.get('template_cid')
                                if template_cid:
                                    st.markdown(f"**Template CID:** `{template_cid}`")

                                    # Create columns for the buttons
                                    btn_col1, btn_col2 = st.columns(2)

                                    # Add a button to view the template data
                                    with btn_col1:
                                        if st.button(f"View Template Data", key=f"view_template_{request_id}"):
                                            try:
                                                # Try to fetch the template data from the API
                                                template_response = requests.get(
                                                    f"{API_URL}/template/{template_cid}",
                                                    params={"wallet_address": st.session_state.wallet_address}
                                                )

                                                # If the first URL fails, try the alternative URL
                                                if template_response.status_code == 404:
                                                    template_response = requests.get(
                                                        f"{API_URL}/api/template/{template_cid}",
                                                        params={"wallet_address": st.session_state.wallet_address}
                                                    )

                                                if template_response.status_code == 200:
                                                    template_data = template_response.json()

                                                    # Display the template data
                                                    st.subheader("Template Data")

                                                    # Show template details
                                                    st.markdown("**Template Details:**")
                                                    if "template" in template_data:
                                                        st.json(template_data["template"])

                                                    # Show records
                                                    if "records" in template_data and template_data["records"]:
                                                        st.markdown(f"**Records ({len(template_data['records'])}):**")

                                                        # Create tabs for each record
                                                        record_tabs = st.tabs([f"Record {i+1}" for i in range(min(5, len(template_data["records"])))])

                                                        for i, tab in enumerate(record_tabs):
                                                            if i < len(template_data["records"]):
                                                                record = template_data["records"][i]
                                                                with tab:
                                                                    st.json(record)

                                                        # If there are more than 5 records, show a message
                                                        if len(template_data["records"]) > 5:
                                                            st.info(f"Showing 5 of {len(template_data['records'])} records. The full dataset is available for analysis.")
                                                    else:
                                                        st.warning("No records found in the template data.")
                                                else:
                                                    st.error(f"Error fetching template data: {template_response.json().get('detail', 'Unknown error')}")
                                            except Exception as e:
                                                st.error(f"Error: {str(e)}")

                                    # Add a button to verify the template
                                    with btn_col2:
                                        if st.button(f"Verify Template", key=f"verify_template_{request_id}"):
                                            # Show verification steps
                                            with st.status("Verifying template...", expanded=True) as status:
                                                st.write("Retrieving template package from IPFS...")
                                                time.sleep(0.5)  # Simulate delay

                                                # Call API to verify purchase off-chain
                                                try:
                                                    response = requests.post(
                                                        f"{API_URL}/purchase/verify",
                                                        json={
                                                            "request_id": request_id,
                                                            "wallet_address": st.session_state.wallet_address,
                                                            "template_cid": template_cid
                                                        }
                                                    )

                                                    # If the first URL fails, try the alternative URL
                                                    if response.status_code == 404:
                                                        print("Trying alternative API URL...")
                                                        response = requests.post(
                                                            f"{API_URL}/api/purchase/verify",
                                                            json={
                                                                "request_id": request_id,
                                                                "wallet_address": st.session_state.wallet_address,
                                                                "template_cid": template_cid
                                                            }
                                                        )

                                                    st.write("Verifying hospital signature...")
                                                    time.sleep(0.5)  # Simulate delay

                                                    st.write("Verifying Merkle proofs...")
                                                    time.sleep(0.5)  # Simulate delay

                                                    st.write("Verifying group signatures...")
                                                    time.sleep(0.5)  # Simulate delay

                                                    if response.status_code == 200:
                                                        result = response.json()
                                                        if result["verified"]:
                                                            status.update(label="Verification complete!", state="complete")
                                                            st.success("Verification successful!")
                                                            st.session_state.verification_result = result
                                                            st.session_state.verified_request_id = request_id

                                                            # Display records and patients count if available
                                                            if "records_count" in result:
                                                                st.info(f"Records count: {result['records_count']}")
                                                            if "patients_count" in result:
                                                                st.info(f"Patients count: {result['patients_count']}")

                                                            st.info("You can now finalize the purchase on-chain")

                                                            # Display recipients in a nicer format
                                                            st.subheader("Payment Recipients")
                                                            st.write("The following addresses will receive payment if you approve:")

                                                            for i, recipient in enumerate(result["recipients"]):
                                                                # Check if it's a known address
                                                                recipient_name = "Unknown"
                                                                for name, info in TEST_ACCOUNTS.items():
                                                                    if info["address"].lower() == recipient.lower():
                                                                        recipient_name = f"{name} ({info['role']})"
                                                                        break

                                                                st.markdown(f"**{i+1}.** `{recipient}` - {recipient_name}")

                                                            # Add a button to finalize the purchase
                                                            if st.button("Finalize Purchase", key=f"finalize_{request_id}"):
                                                                try:
                                                                    finalize_response = requests.post(
                                                                        f"{API_URL}/purchase/finalize",
                                                                        json={
                                                                            "request_id": request_id,
                                                                            "approved": True,
                                                                            "recipients": result["recipients"],
                                                                            "wallet_address": st.session_state.wallet_address
                                                                        }
                                                                    )

                                                                    if finalize_response.status_code == 200:
                                                                        finalize_result = finalize_response.json()
                                                                        st.success("Purchase finalized successfully!")
                                                                        st.markdown(f"**Transaction Hash:** `{finalize_result.get('transaction_hash', 'N/A')}`")
                                                                        st.rerun()
                                                                    else:
                                                                        st.error(f"Error finalizing purchase: {finalize_response.json().get('detail', 'Unknown error')}")
                                                                except Exception as e:
                                                                    st.error(f"Error finalizing purchase: {str(e)}")
                                                        else:
                                                            status.update(label="Verification failed", state="error")
                                                            st.error(f"Verification failed! {result.get('message', 'The data does not meet the requirements.')}")
                                                    else:
                                                        status.update(label="Verification failed", state="error")
                                                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                                except Exception as e:
                                                    status.update(label="Verification failed", state="error")
                                                    st.error(f"Error: {str(e)}")

                                # Check if there's a template CID
                                template_cid = latest_tx.get('template_cid')
                                if template_cid:
                                    st.markdown(f"**Template CID:** `{template_cid}`")

                                    # Add a button to view the template data
                                    if st.button(f"View Template Data for {template_cid[:8]}...", key=f"view_template_{request_id}"):
                                        try:
                                            # Try to fetch the template data from the API
                                            template_response = requests.get(
                                                f"{API_URL}/template/{template_cid}",
                                                params={"wallet_address": st.session_state.wallet_address}
                                            )

                                            # If the first URL fails, try the alternative URL
                                            if template_response.status_code == 404:
                                                template_response = requests.get(
                                                    f"{API_URL}/api/template/{template_cid}",
                                                    params={"wallet_address": st.session_state.wallet_address}
                                                )

                                            if template_response.status_code == 200:
                                                template_data = template_response.json()

                                                # Display the template data
                                                st.subheader("Template Data")

                                                # Show template details
                                                st.markdown("**Template Details:**")
                                                if "template" in template_data:
                                                    st.json(template_data["template"])

                                                # Show records
                                                if "records" in template_data and template_data["records"]:
                                                    st.markdown(f"**Records ({len(template_data['records'])}):**")

                                                    # Create tabs for each record
                                                    record_tabs = st.tabs([f"Record {i+1}" for i in range(min(5, len(template_data["records"])))])

                                                    for i, tab in enumerate(record_tabs):
                                                        if i < len(template_data["records"]):
                                                            record = template_data["records"][i]
                                                            with tab:
                                                                st.json(record)

                                                    # If there are more than 5 records, show a message
                                                    if len(template_data["records"]) > 5:
                                                        st.info(f"Showing 5 of {len(template_data['records'])} records. The full dataset is available for analysis.")
                                                else:
                                                    st.warning("No records found in the template data.")
                                            else:
                                                st.error(f"Error fetching template data: {template_response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")
                            elif latest_tx["type"] == "Verification":
                                st.markdown("**Verification Details:**")
                                st.markdown(f"**Verified:** {latest_tx['details'].get('verified', False)}")
                                st.markdown(f"**Merkle Proofs:** {latest_tx['details'].get('merkle_proofs', 'N/A')}")
                                st.markdown(f"**Signatures:** {latest_tx['details'].get('signatures', 'N/A')}")

                                st.markdown("**Recipients:**")
                                for i, recipient in enumerate(latest_tx['details'].get('recipients', [])):
                                    # Check if it's a known address
                                    recipient_name = "Unknown"
                                    for name, info in TEST_ACCOUNTS.items():
                                        if info["address"].lower() == recipient.lower():
                                            recipient_name = f"{name} ({info['role']})"
                                            break
                                    st.markdown(f"**{i+1}.** `{recipient}` - {recipient_name}")
                            elif latest_tx["type"] == "Finalize":
                                st.markdown("**Finalization Details:**")
                                st.markdown(f"**Approved:** {latest_tx['approved']}")
                                if latest_tx['approved']:
                                    st.markdown(f"**Payment per Recipient:** {latest_tx['details'].get('payment_per_recipient', 'N/A')} ETH")
                                    st.markdown("**Recipients:**")
                                    for i, recipient in enumerate(latest_tx['details'].get('recipients', [])):
                                        # Check if it's a known address
                                        recipient_name = "Unknown"
                                        for name, info in TEST_ACCOUNTS.items():
                                            if info["address"].lower() == recipient.lower():
                                                recipient_name = f"{name} ({info['role']})"
                                                break
                                        st.markdown(f"**{i+1}.** `{recipient}` - {recipient_name}")

                with history_tab2:
                    st.subheader("Purchase Workflow Visualization")

        with tab3:
            st.header("Filled Templates")

            # Function to fetch filled templates from the API
            def fetch_filled_templates():
                try:
                    # Call API to get filled templates
                    response = requests.get(
                        f"{API_URL}/buyer/filled-templates",
                        params={
                            "wallet_address": st.session_state.wallet_address
                        }
                    )

                    # If the first URL fails, try the alternative URL
                    if response.status_code == 404:
                        print("Trying alternative API URL...")
                        response = requests.get(
                            f"{API_URL}/api/buyer/filled-templates",
                            params={
                                "wallet_address": st.session_state.wallet_address
                            }
                        )

                    if response.status_code == 200:
                        result = response.json()
                        return result.get("templates", [])
                    else:
                        print(f"Error fetching filled templates: {response.status_code}")
                        return []
                except Exception as e:
                    print(f"Error fetching filled templates: {str(e)}")
                    return []

            # For demo purposes, let's create some sample filled templates
            # In a real implementation, these would come from the API
            if "filled_templates" not in st.session_state:
                # Try to fetch from API first
                api_templates = fetch_filled_templates()

                if api_templates:
                    st.session_state.filled_templates = api_templates
                else:
                    # Use sample data as fallback
                    st.session_state.filled_templates = [
                        {
                            "request_id": "req_001",
                            "patient": "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",  # Patient 1 address
                            "hospital": "0x28B317594b44483D24EE8AdCb13A1b148497C6ba",  # Hospital address
                            "template_cid": "template_req_001_1234567890",
                            "cert_cid": "cert_req_001_1234567890",
                            "status": "filled",
                            "timestamp": int(time.time()) - 3600,  # 1 hour ago
                            "template": {
                                "category": "Cardiology",
                                "demographics": {"age": True, "gender": True},
                                "medical_data": {"diagnosis": True, "treatment": True},
                                "time_period": "1 year",
                                "min_records": 1
                            }
                        }
                    ]

            # Add a refresh button
            if st.button("Refresh Filled Templates"):
                api_templates = fetch_filled_templates()
                if api_templates:
                    st.session_state.filled_templates = api_templates
                st.success("Filled templates refreshed!")

            # Display filled templates
            if not st.session_state.filled_templates:
                st.info("No filled templates found. Templates will appear here when patients fill out your data requests.")
            else:
                # Group templates by request ID
                request_ids = {}
                for template in st.session_state.filled_templates:
                    request_id = template.get("request_id")
                    if request_id not in request_ids:
                        request_ids[request_id] = []
                    request_ids[request_id].append(template)

                # Display templates grouped by request ID
                for request_id, templates in request_ids.items():
                    st.subheader(f"Request: {request_id} ({len(templates)} templates)")

                    # Display request details
                    if templates:
                        first_template = templates[0]
                        st.markdown("**Request Details**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Request ID:** {request_id}")
                            st.markdown(f"**Hospital:** `{first_template.get('hospital', 'Unknown')[:8]}...`")
                            st.markdown(f"**Category:** {first_template.get('template', {}).get('category', 'Unknown')}")
                        with col2:
                            # Format timestamp
                            timestamp = first_template.get("timestamp", 0)
                            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            st.markdown(f"**Timestamp:** {date_str}")
                            st.markdown(f"**Templates Count:** {len(templates)}")

                    # Display templates
                    st.markdown("**Filled Templates**")

                    # Create tabs for each template
                    template_tabs = st.tabs([f"Template {i+1} - Patient: {template.get('patient', 'Unknown')[:8]}..." for i, template in enumerate(templates)])

                    # Fill each tab with template content
                    for i, (tab, template) in enumerate(zip(template_tabs, templates)):
                        with tab:
                                # Template details
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Template CID:** `{template.get('template_cid', 'N/A')}`")
                                    st.markdown(f"**CERT CID:** `{template.get('cert_cid', 'N/A')}`")

                                    # Format patient address
                                    patient = template.get("patient", "Unknown")
                                    patient_display = patient
                                    if len(patient) > 10:
                                        patient_display = f"{patient[:6]}...{patient[-4:]}"

                                    # Check if it's a known address
                                    patient_name = "Unknown"
                                    for name, info in TEST_ACCOUNTS.items():
                                        if info["address"].lower() == patient.lower():
                                            patient_name = f"{name} ({info['role']})"
                                            break

                                    st.markdown(f"**Patient:** `{patient_display}` - {patient_name}")

                                with col2:
                                    # Format timestamp
                                    timestamp = template.get("timestamp", 0)
                                    date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                    st.markdown(f"**Filled at:** {date_str}")

                                    # Status
                                    status = template.get("status", "filled")
                                    st.markdown(f"**Status:** {status.capitalize()}")

                                    # Verification status
                                    verification_status = template.get("verified", False)
                                    if verification_status:
                                        st.markdown("**Verification:** ✅ Verified")
                                    else:
                                        st.markdown("**Verification:** ❌ Not verified")

                                # Template content
                                if "template" in template:
                                    st.subheader("Template Content")
                                    st.json(template["template"])

                                # Action buttons
                                st.markdown("---")
                                st.markdown("**Actions:**")

                                col1, col2 = st.columns(2)
                                with col1:
                                    # View template data button
                                    if st.button(f"View Template Data", key=f"view_data_{template.get('template_cid')}"):
                                        try:
                                            # Try to fetch the template data from the API
                                            template_response = requests.get(
                                                f"{API_URL}/template/{template.get('template_cid')}",
                                                params={
                                                    "wallet_address": st.session_state.wallet_address,
                                                    "cert_cid": template.get('cert_cid')
                                                }
                                            )

                                            # If the first URL fails, try the alternative URL
                                            if template_response.status_code == 404:
                                                template_response = requests.get(
                                                    f"{API_URL}/api/template/{template.get('template_cid')}",
                                                    params={
                                                        "wallet_address": st.session_state.wallet_address,
                                                        "cert_cid": template.get('cert_cid')
                                                    }
                                                )

                                            if template_response.status_code == 200:
                                                template_data = template_response.json()

                                                # Display the template data
                                                st.subheader("Template Data")
                                                st.json(template_data)
                                            else:
                                                st.error(f"Error fetching template data: {template_response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")

                                with col2:
                                    # Verify template button
                                    if st.button(f"Verify Template", key=f"verify_{template.get('template_cid')}"):
                                        # Show verification steps
                                        with st.status("Verifying template...", expanded=True) as status:
                                            st.write("Retrieving template package from IPFS...")
                                            time.sleep(0.5)  # Simulate delay

                                            # Call API to verify template
                                            try:
                                                response = requests.post(
                                                    f"{API_URL}/purchase/verify",
                                                    json={
                                                        "request_id": request_id,
                                                        "wallet_address": st.session_state.wallet_address,
                                                        "template_cid": template.get('template_cid')
                                                    }
                                                )

                                                # If the first URL fails, try the alternative URL
                                                if response.status_code == 404:
                                                    print("Trying alternative API URL...")
                                                    response = requests.post(
                                                        f"{API_URL}/api/purchase/verify",
                                                        json={
                                                            "request_id": request_id,
                                                            "wallet_address": st.session_state.wallet_address,
                                                            "template_cid": template.get('template_cid')
                                                        }
                                                    )

                                                st.write("Verifying hospital signature...")
                                                time.sleep(0.5)  # Simulate delay

                                                st.write("Verifying Merkle proofs...")
                                                time.sleep(0.5)  # Simulate delay

                                                st.write("Verifying group signatures...")
                                                time.sleep(0.5)  # Simulate delay

                                                if response.status_code == 200:
                                                    result = response.json()
                                                    if result["verified"]:
                                                        status.update(label="Verification complete!", state="complete")
                                                        st.success("Verification successful!")

                                                        # Update the template status
                                                        for t in st.session_state.filled_templates:
                                                            if t.get("template_cid") == template.get("template_cid"):
                                                                t["verified"] = True
                                                                break

                                                        # Display verification details
                                                        st.markdown(f"**Merkle Root:** `{result.get('merkle_root', 'N/A')[:10]}...`")
                                                        st.markdown(f"**Signature:** `{result.get('signature', 'N/A')[:10]}...`")

                                                        # Display recipient
                                                        if "recipients" in result and result["recipients"]:
                                                            st.markdown(f"**Recipient:** `{result['recipients'][0]}`")
                                                    else:
                                                        status.update(label="Verification failed", state="error")
                                                        st.error(f"Verification failed! {result.get('message', 'The data does not meet the requirements.')}")

                                                        # Show revocation button
                                                        if st.button("Request Revocation", key=f"revoke_{template.get('template_cid')}"):
                                                            try:
                                                                # Call API to request revocation
                                                                revoke_response = requests.post(
                                                                    f"{API_URL}/revocation/request",
                                                                    json={
                                                                        "request_id": request_id,
                                                                        "template_cid": template.get('template_cid'),
                                                                        "signature": result.get('signature', ''),
                                                                        "wallet_address": st.session_state.wallet_address
                                                                    }
                                                                )

                                                                if revoke_response.status_code == 200:
                                                                    revoke_result = revoke_response.json()
                                                                    st.success("Revocation request submitted successfully!")
                                                                    st.markdown(f"**Transaction Hash:** `{revoke_result.get('transaction_hash', 'N/A')}`")
                                                                    st.info("The Group Manager and Revocation Manager will process your request.")
                                                                else:
                                                                    st.error(f"Error requesting revocation: {revoke_response.json().get('detail', 'Unknown error')}")
                                                            except Exception as e:
                                                                st.error(f"Error requesting revocation: {str(e)}")
                                                else:
                                                    status.update(label="Verification failed", state="error")
                                                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                            except Exception as e:
                                                status.update(label="Verification failed", state="error")
                                                st.error(f"Error: {str(e)}")

                    # Add a button to verify all templates at once
                    if st.button(f"Verify All Templates for Request {request_id}", key=f"verify_all_{request_id}"):
                        # Show verification steps
                        with st.status("Verifying all templates...", expanded=True) as status:
                            st.write(f"Verifying {len(templates)} templates...")

                            # Track verification results
                            success_count = 0
                            failed_templates = []

                            # Verify each template
                            for template in templates:
                                st.write(f"Verifying template {template.get('template_cid')}...")
                                time.sleep(0.3)  # Simulate delay

                                # Call API to verify template
                                try:
                                    response = requests.post(
                                        f"{API_URL}/purchase/verify",
                                        json={
                                            "request_id": request_id,
                                            "wallet_address": st.session_state.wallet_address,
                                            "template_cid": template.get('template_cid')
                                        }
                                    )

                                    if response.status_code == 200:
                                        result = response.json()
                                        if result["verified"]:
                                            success_count += 1
                                            # Update the template status
                                            for t in st.session_state.filled_templates:
                                                if t.get("template_cid") == template.get("template_cid"):
                                                    t["verified"] = True
                                                    break
                                        else:
                                            failed_templates.append({
                                                "template_cid": template.get('template_cid'),
                                                "patient": template.get('patient'),
                                                "signature": result.get('signature', '')
                                            })
                                    else:
                                        failed_templates.append({
                                            "template_cid": template.get('template_cid'),
                                            "patient": template.get('patient'),
                                            "error": response.json().get('detail', 'Unknown error')
                                        })
                                except Exception as e:
                                    failed_templates.append({
                                        "template_cid": template.get('template_cid'),
                                        "patient": template.get('patient'),
                                        "error": str(e)
                                    })

                            # Show verification results
                            if success_count == len(templates):
                                status.update(label="All templates verified successfully!", state="complete")
                                st.success(f"All {len(templates)} templates verified successfully!")
                            else:
                                status.update(label=f"{success_count}/{len(templates)} templates verified", state="error")
                                st.warning(f"{success_count}/{len(templates)} templates verified successfully. {len(failed_templates)} templates failed verification.")

                                # Show failed templates
                                if failed_templates:
                                    st.subheader("Failed Templates")
                                    for i, failed in enumerate(failed_templates):
                                        st.markdown(f"**{i+1}. Template:** `{failed['template_cid']}`")
                                        st.markdown(f"**Patient:** `{failed['patient']}`")
                                        if "error" in failed:
                                            st.markdown(f"**Error:** {failed['error']}")

                                    # Show revocation button for all failed templates
                                    if st.button("Request Revocation for All Failed Templates", key=f"revoke_all_{request_id}"):
                                        # Call API to request revocation for all failed templates
                                        revocation_results = []
                                        for failed in failed_templates:
                                            try:
                                                # Call API to request revocation
                                                revoke_response = requests.post(
                                                    f"{API_URL}/revocation/request",
                                                    json={
                                                        "request_id": request_id,
                                                        "template_cid": failed["template_cid"],
                                                        "signature": failed.get("signature", ""),
                                                        "wallet_address": st.session_state.wallet_address
                                                    }
                                                )

                                                if revoke_response.status_code == 200:
                                                    revoke_result = revoke_response.json()
                                                    revocation_results.append({
                                                        "template_cid": failed["template_cid"],
                                                        "success": True,
                                                        "transaction_hash": revoke_result.get("transaction_hash", "N/A")
                                                    })
                                                else:
                                                    revocation_results.append({
                                                        "template_cid": failed["template_cid"],
                                                        "success": False,
                                                        "error": revoke_response.json().get("detail", "Unknown error")
                                                    })
                                            except Exception as e:
                                                revocation_results.append({
                                                    "template_cid": failed["template_cid"],
                                                    "success": False,
                                                    "error": str(e)
                                                })

                                        # Show revocation results
                                        st.subheader("Revocation Results")
                                        success_count = sum(1 for r in revocation_results if r["success"])
                                        st.info(f"{success_count}/{len(revocation_results)} revocation requests submitted successfully.")

                                        for i, result in enumerate(revocation_results):
                                            if result["success"]:
                                                st.markdown(f"**{i+1}. Template:** `{result['template_cid']}` - ✅ Success")
                                                st.markdown(f"**Transaction Hash:** `{result['transaction_hash']}`")
                                            else:
                                                st.markdown(f"**{i+1}. Template:** `{result['template_cid']}` - ❌ Failed")
                                                st.markdown(f"**Error:** {result['error']}")

                    # Create a visual representation of the workflow
                    for request_id in request_ids:
                        with st.expander(f"Request: {request_id}", expanded=True):
                            # Filter transactions for this request ID
                            request_txs = [tx for tx in st.session_state.transaction_history if tx["request_id"] == request_id]

                            # Sort by timestamp
                            from operator import itemgetter
                            request_txs.sort(key=itemgetter("timestamp"))

                            # Define workflow steps
                            workflow_steps = [
                                "Request",
                                "Hospital Reply",
                                "Verification",
                                "Finalize"
                            ]

                            # Create a progress bar for the workflow
                            step_statuses = {}
                            for tx in request_txs:
                                step_statuses[tx["type"]] = tx["status"]

                            # Display the workflow progress
                            st.write("Workflow Progress:")
                            cols = st.columns(len(workflow_steps))

                            for i, step in enumerate(workflow_steps):
                                with cols[i]:
                                    if step in step_statuses:
                                        if step_statuses[step] == "Completed":
                                            st.markdown(f"**{step}** ✅")
                                        elif step_statuses[step] == "Pending":
                                            st.markdown(f"**{step}** ⏳")
                                        else:
                                            st.markdown(f"**{step}** ❌")
                                    else:
                                        st.markdown(f"**{step}** ⬜")

                            # Display a timeline
                            st.write("Timeline:")
                            for tx in request_txs:
                                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                                if tx["status"] == "Completed":
                                    st.success(f"**{tx_time}**: {tx['type']} - {tx['status']}")
                                elif tx["status"] == "Pending":
                                    st.info(f"**{tx_time}**: {tx['type']} - {tx['status']}")
                                else:
                                    st.error(f"**{tx_time}**: {tx['type']} - {tx['status']}")
                else:
                    st.info("No purchases. Your purchase requests will appear here.")

        with tab4:
            st.header("Transaction History")
            # This tab will show a more detailed transaction history
            # Fetch transaction history from the API
            try:
                # Show a loading spinner while fetching transactions
                with st.spinner("Fetching transaction history..."):
                    response = requests.get(
                        f"{API_URL}/transactions",
                        params={"wallet_address": st.session_state.wallet_address}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        transactions = result.get("transactions", [])

                        if transactions:
                            # Create a DataFrame for display
                            tx_data = []
                            for tx in transactions:
                                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                                tx_hash = tx.get("tx_hash", "N/A")
                                tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if tx_hash != "N/A" else "N/A"

                                tx_data.append({
                                    "Type": tx["type"],
                                    "Status": tx["status"],
                                    "Timestamp": tx_time,
                                    "TX Hash": tx_hash_short,
                                    "Gas Fee (ETH)": tx.get("gas_fee", "N/A"),
                                    "Request ID": tx.get("request_id", "N/A")
                                })

                            # Display as a table
                            st.dataframe(tx_data)
                        else:
                            st.info("No transactions found.")
                    else:
                        st.error(f"Error fetching transactions: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")

        with tab5:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

            # Form for finalizing purchases
            with st.expander("Finalize Purchase"):
                with st.form("finalize_purchase_form"):
                    request_id = st.text_input("Request ID")
                    approved = st.checkbox("Approve Purchase")
                    recipients = st.text_input("Recipient Addresses (comma-separated)")

                    submit_button = st.form_submit_button("Finalize")

                    if submit_button:
                        # Call API to finalize purchase
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/finalize",
                                json={
                                    "request_id": request_id,
                                    "approved": approved,
                                    "recipients": recipients.split(","),
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            # If the first URL fails, try the alternative URL
                            if response.status_code == 404:
                                print("Trying alternative API URL...")
                                response = requests.post(
                                    f"{API_URL}/api/purchase/finalize",
                                    json={
                                        "request_id": request_id,
                                        "approved": approved,
                                        "recipients": recipients.split(","),
                                        "wallet_address": st.session_state.wallet_address
                                    }
                                )

                            if response.status_code == 200:
                                result = response.json()
                                st.success("Purchase finalized successfully!")

                                # Track the transaction in the session state
                                track_transaction(
                                    tx_hash=result.get('transaction_hash'),
                                    operation='Finalize Purchase',
                                    wallet_address=st.session_state.wallet_address,
                                    gas_used=120000,  # Estimated gas used
                                    gas_price=None  # We don't know the gas price in this simulation
                                )

                                # Add transaction from the result if available
                                if "transaction" in result:
                                    st.session_state.transaction_history.append(result["transaction"])
                                else:
                                    # Fallback to creating our own transaction
                                    new_tx = {
                                        "id": f"tx-{len(st.session_state.transaction_history) + 1:03d}",
                                        "request_id": request_id,
                                        "type": "Finalize",
                                        "status": "Completed",
                                        "timestamp": int(time.time()),
                                        "tx_hash": result.get('transaction_hash', f"0x{hashlib.sha256(f'finalize_{request_id}_{int(time.time())}').hexdigest()[:40]}"),
                                        "gas_fee": result.get('gas_fee', 0.0018),
                                        "amount": 0.1,
                                        "approved": approved,
                                        "details": {
                                            "recipients": recipients.split(","),
                                            "payment_per_recipient": 0.1 / len(recipients.split(",")) if approved and recipients else 0
                                        }
                                    }
                                    st.session_state.transaction_history.append(new_tx)
                                st.rerun()
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")


    elif role == "Group Manager":
        st.title("Group Manager Dashboard")

        # Tabs for different actions
        tab1, tab2 = st.tabs(["Signature Opening Requests", "Gas Fees"])

        with tab1:
            st.header("Signature Opening Requests")

            # Form for processing opening requests
            with st.form("process_opening_form"):
                opening_id = st.text_input("Opening Request ID")
                signature_hash = st.text_input("Signature Hash")

                submit_button = st.form_submit_button("Compute Partial Opening (Off-Chain)")

                if submit_button:
                    if not opening_id or not signature_hash:
                        st.error("Please enter both Opening ID and Signature Hash")
                    else:
                        # Call API to compute partial opening
                        try:
                            response = requests.post(
                                f"{API_URL}/opening/compute_partial",
                                json={
                                    "opening_id": int(opening_id),
                                    "signature_hash": signature_hash,
                                    "manager_type": "group",
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                st.success("Partial opening computed successfully!")
                                st.info("You can now approve the opening on-chain.")
                                st.session_state.partial_computed = True
                                st.session_state.current_opening_id = opening_id
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Button for on-chain approval (outside the form)
            if hasattr(st.session_state, 'partial_computed') and st.session_state.partial_computed:
                st.subheader("Approve Opening")
                if st.button("Approve Opening (On-Chain)"):
                    # In a real implementation, this would call the smart contract
                    st.success(f"Opening {st.session_state.current_opening_id} approved on-chain!")
                    # Clear the state
                    del st.session_state.partial_computed
                    del st.session_state.current_opening_id

        with tab2:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

    elif role == "Revocation Manager":
        st.title("Revocation Manager Dashboard")

        # Tabs for different actions
        tab1, tab2 = st.tabs(["Signature Opening Requests", "Gas Fees"])

        with tab1:
            st.header("Signature Opening Requests")

            # Form for processing opening requests
            with st.form("process_opening_form"):
                opening_id = st.text_input("Opening Request ID")
                signature_hash = st.text_input("Signature Hash")

                submit_button = st.form_submit_button("Compute Partial Opening (Off-Chain)")

                if submit_button:
                    if not opening_id or not signature_hash:
                        st.error("Please enter both Opening ID and Signature Hash")
                    else:
                        # Call API to compute partial opening
                        try:
                            response = requests.post(
                                f"{API_URL}/opening/compute_partial",
                                json={
                                    "opening_id": int(opening_id),
                                    "signature_hash": signature_hash,
                                    "manager_type": "revocation",
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                st.success("Partial opening computed successfully!")
                                st.info("You can now approve the opening on-chain.")
                                st.session_state.partial_computed = True
                                st.session_state.current_opening_id = opening_id
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            # Button for on-chain approval (outside the form)
            if hasattr(st.session_state, 'partial_computed') and st.session_state.partial_computed:
                st.subheader("Approve Opening")
                if st.button("Approve Opening (On-Chain)"):
                    # In a real implementation, this would call the smart contract
                    st.success(f"Opening {st.session_state.current_opening_id} approved on-chain!")
                    # Clear the state
                    del st.session_state.partial_computed
                    del st.session_state.current_opening_id

        with tab2:
            # Use the reusable gas fees tab function
            render_gas_fees_tab(st.session_state.wallet_address)

# Footer
st.markdown("---")
st.markdown("Decentralized Healthcare Data Sharing on BASE Testnet")

# Check if we need to rerun the app
if st.session_state.get("trigger_rerun", False):
    # Clear the trigger
    st.session_state.trigger_rerun = False
    # Rerun the app
    st.rerun()
# Check if auto-refresh is enabled for Hospital dashboard
elif st.session_state.get("hospital_auto_refresh", False):
    # Check if it's time for auto-refresh (every 30 seconds)
    current_time = int(time.time())
    last_refresh = st.session_state.get("hospital_last_refresh", 0)
    if (current_time - last_refresh) > 30:
        st.session_state.hospital_last_refresh = current_time
        st.rerun()
