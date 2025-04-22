import streamlit as st
import requests
import json
import os
import datetime
import time
import base64
from web3 import Web3
import streamlit.components.v1 as components
from dotenv import load_dotenv
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
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x7ab1C0aA17fAA544AE2Ca48106b92836A9eeF9a6")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")

# Initialize Web3 with Coinbase Cloud RPC
w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC_URL))

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
st.set_page_config(
    page_title="Healthcare Data Sharing",
    page_icon="🏥",
    layout="wide"
)

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
    st.session_state.wallet_connected = True

    # Get the selected account from session state
    selected_account = st.session_state.get("selected_account")

    # If no account is selected, use the first account in the list
    if not selected_account or selected_account not in TEST_ACCOUNTS:
        selected_account = list(TEST_ACCOUNTS.keys())[0]
        st.session_state.selected_account = selected_account

    # Get the account info from the TEST_ACCOUNTS dictionary
    account_info = TEST_ACCOUNTS[selected_account]
    st.session_state.wallet_address = account_info["address"]
    st.session_state.private_key = account_info["private_key"]

    # Set the initial role based on the account type
    st.session_state.selected_role = account_info["role"]

    # Debug info
    print(f"Connected as {selected_account} with role {st.session_state.selected_role}")

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
        tab1, tab2, tab3 = st.tabs(["My Records", "Share Records", "Data Requests"])

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
                    with st.expander(f"{record.get('diagnosis', 'Medical Record')} - {record.get('date', 'Unknown date')}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Date:** {record.get('date', 'N/A')}")
                            st.markdown(f"**Diagnosis:** {record.get('diagnosis', 'N/A')}")
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
                            st.markdown(f"**Verified:** ✅")

                        st.markdown("**Notes:**")
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
            st.header("Data Purchase Requests")

            # Form for requesting data purchase
            with st.form("purchase_request_form"):
                template_hash = st.text_input("Template Hash")
                amount = st.number_input("Escrow Amount (ETH)", min_value=0.01, value=1.0, step=0.1)

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

            col1, col2 = st.columns(2)
            with col1:
                request_id = st.text_input("Request ID")
            with col2:
                template_cid = st.text_input("Template CID")

            if st.button("Verify Purchase (Off-Chain)"):
                if not request_id or not template_cid:
                    st.error("Please enter both Request ID and Template CID")
                else:
                    # Call API to verify purchase off-chain
                    try:
                        response = requests.post(
                            f"{API_URL}/purchase/verify",
                            json={
                                "request_id": request_id,
                                "template_cid": template_cid,
                                "wallet_address": st.session_state.wallet_address
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            if result["verified"]:
                                st.success("Verification successful!")
                                st.session_state.verification_result = result
                                st.session_state.verified_request_id = request_id
                                st.info("You can now finalize the purchase on-chain")

                                # Display recipients
                                st.subheader("Payment Recipients")
                                for i, recipient in enumerate(result["recipients"]):
                                    st.text(f"{i+1}. {recipient}")
                            else:
                                st.error("Verification failed! The data does not meet the requirements.")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            # Finalize purchase button (only shown after verification)
            if hasattr(st.session_state, 'verification_result') and hasattr(st.session_state, 'verified_request_id'):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Finalize Purchase (Approve)"):
                        # Call API to finalize purchase with approval
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/finalize",
                                json={
                                    "request_id": st.session_state.verified_request_id,
                                    "approved": True,
                                    "recipients": st.session_state.verification_result["recipients"],
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                st.success("Purchase finalized successfully! Payment has been distributed.")
                                # Clear the verification result
                                del st.session_state.verification_result
                                del st.session_state.verified_request_id
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                with col2:
                    if st.button("Finalize Purchase (Reject)"):
                        # Call API to finalize purchase with rejection
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/finalize",
                                json={
                                    "request_id": st.session_state.verified_request_id,
                                    "approved": False,
                                    "recipients": [],
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                st.success("Purchase rejected. Your escrow has been refunded.")
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

                if st.button("Check Opening Status"):
                    # In a real implementation, this would check the blockchain
                    st.info("Opening request is being processed...")

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
        tab1, tab2 = st.tabs(["Create Records", "Shared Records"])

        with tab1:
            st.header("Create Patient Records")

            # Form for creating records
            with st.form("create_record_form"):
                patient_address = st.text_input("Patient Wallet Address",
                                              help="Enter the patient's wallet address")
                date = st.date_input("Date")
                diagnosis = st.text_input("Diagnosis")
                notes = st.text_area("Notes")
                hospital_info = st.text_input("Hospital Info", value="General Hospital",
                                            help="Information about the hospital")

                submit_button = st.form_submit_button("Create and Sign Record")

                if submit_button:
                    if not patient_address:
                        st.error("Please enter the patient's wallet address")
                    else:
                        # Step 1: Create the record
                        record_data = {
                            "patientID": patient_address,  # Using patientID to match the expected format
                            "date": str(date),
                            "diagnosis": diagnosis,
                            "notes": notes,
                            "doctorID": st.session_state.wallet_address,  # Using doctorID to match the expected format
                            "hospitalInfo": hospital_info
                        }

                        # Display the record being created
                        st.info("Creating and signing the following record:")
                        st.json(record_data)

                        # Step 2: Call API to sign the record with group signature
                        try:
                            with st.spinner("Signing record with group signature..."):
                                response = requests.post(
                                    f"{API_URL}/records/sign",
                                    json=record_data
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

                                        if store_response.status_code == 200:
                                            store_result = store_response.json()
                                            st.success("Record encrypted and stored on IPFS!")

                                            # Display IPFS and blockchain details
                                            st.markdown(f"**IPFS CID:** `{store_result['cid']}`")
                                            st.markdown(f"**Transaction Hash:** `{store_result.get('txHash', 'N/A')}`")

                                            # Create a certificate (CERT) for the patient
                                            cert = {
                                                "cid": store_result['cid'],
                                                "merkleRoot": signed_data['merkleRoot'],  # IDRecord
                                                "signature": signed_data['signature'],     # Signed(IDRecord)
                                                "eId": store_result.get('eId', 'PCS_encrypted_hospital_info_and_key'),  # PCS(HospitalInfo||K_patient)
                                                "doctorId": st.session_state.wallet_address,
                                                "timestamp": int(time.time())
                                            }

                                            # Display the certificate
                                            st.subheader("Certificate (CERT) for Patient")
                                            st.info("Share this certificate with the patient so they can access their record:")

                                            # Explain the certificate components
                                            st.markdown("**Certificate Components:**")
                                            st.markdown("- **cid**: IPFS content identifier for the encrypted record")
                                            st.markdown("- **merkleRoot**: IDRecord (Merkle root hash of the record)")
                                            st.markdown("- **signature**: Group signature on the IDRecord")
                                            st.markdown("- **eId**: PCS-encrypted hospital info and patient key")
                                            st.markdown("- **doctorId**: Doctor's wallet address")
                                            st.markdown("- **timestamp**: When the record was created")

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

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Patient ID:** {record.get('patientID', 'N/A')}")
                                    st.markdown(f"**Date:** {record.get('date', 'N/A')}")
                                    st.markdown(f"**Diagnosis:** {record.get('diagnosis', 'N/A')}")

                                with col2:
                                    st.markdown(f"**Doctor ID:** {record.get('doctorID', 'N/A')}")
                                    st.markdown(f"**Shared By:** {result.get('shared_by', 'N/A')}")
                                    shared_at = datetime.datetime.fromtimestamp(result.get('shared_at', 0))
                                    st.markdown(f"**Shared At:** {shared_at.strftime('%Y-%m-%d %H:%M:%S')}")

                                st.markdown("**Notes:**")
                                st.text_area("Notes", value=record.get('notes', ''), height=150, disabled=True)

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

    elif role == "Hospital":
        st.title("Hospital Dashboard")

        # Tabs for different actions
        tab1, tab2, tab3 = st.tabs(["Purchase Requests", "Manage Group", "Signature Openings"])

        with tab1:
            st.header("Data Purchase Requests")
            st.info("No pending requests. Requests from buyers will appear here.")

            # Form for replying to purchase requests
            with st.expander("Reply to Purchase Request"):
                with st.form("reply_purchase_form"):
                    request_id = st.text_input("Request ID")
                    template_cid = st.text_input("Template CID")

                    submit_button = st.form_submit_button("Submit Reply")

                    if submit_button:
                        # Call API to reply to purchase request
                        try:
                            response = requests.post(
                                f"{API_URL}/purchase/reply",
                                json={
                                    "request_id": request_id,
                                    "template_cid": template_cid,
                                    "wallet_address": st.session_state.wallet_address
                                }
                            )

                            if response.status_code == 200:
                                st.success("Reply submitted successfully!")
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

    elif role == "Buyer":
        st.title("Data Buyer Dashboard")

        # Tabs for different actions
        tab1, tab2 = st.tabs(["Request Data", "My Purchases"])

        with tab1:
            st.header("Request Healthcare Data")

            # Form for requesting data
            with st.form("request_data_form"):
                template_hash = st.text_input("Template Hash")
                amount = st.number_input("Escrow Amount (ETH)", min_value=0.001, step=0.001)

                submit_button = st.form_submit_button("Submit Request")

                if submit_button:
                    # Call API to request data purchase
                    try:
                        response = requests.post(
                            f"{API_URL}/purchase/request",
                            json={
                                "template_hash": template_hash,
                                "amount": amount,
                                "wallet_address": st.session_state.wallet_address
                            }
                        )

                        if response.status_code == 200:
                            st.success("Request submitted successfully!")
                            st.json(response.json())
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        with tab2:
            st.header("My Purchase Requests")
            st.info("No purchases. Your purchase requests will appear here.")

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

                            if response.status_code == 200:
                                st.success("Purchase finalized successfully!")
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

    elif role == "Group Manager":
        st.title("Group Manager Dashboard")

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

        # Button for on-chain approval
        if hasattr(st.session_state, 'partial_computed') and st.session_state.partial_computed:
            if st.button("Approve Opening (On-Chain)"):
                # In a real implementation, this would call the smart contract
                st.success(f"Opening {st.session_state.current_opening_id} approved on-chain!")
                # Clear the state
                del st.session_state.partial_computed
                del st.session_state.current_opening_id

    elif role == "Revocation Manager":
        st.title("Revocation Manager Dashboard")

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

        # Button for on-chain approval
        if hasattr(st.session_state, 'partial_computed') and st.session_state.partial_computed:
            if st.button("Approve Opening (On-Chain)"):
                # In a real implementation, this would call the smart contract
                st.success(f"Opening {st.session_state.current_opening_id} approved on-chain!")
                # Clear the state
                del st.session_state.partial_computed
                del st.session_state.current_opening_id

# Footer
st.markdown("---")
st.markdown("Decentralized Healthcare Data Sharing on BASE Testnet")

# Check if we need to rerun the app
if st.session_state.get("trigger_rerun", False):
    # Clear the trigger
    st.session_state.trigger_rerun = False
    # Rerun the app
    st.rerun()
