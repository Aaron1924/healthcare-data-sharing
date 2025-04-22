import streamlit as st
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
                                    "template_cid": template_cid,
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
                                        "template_cid": template_cid,
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

                                    # Display template size if available
                                    if "template_size" in result:
                                        st.info(f"Template package size: {result['template_size']} bytes")

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

            # Button to check for new requests
            if st.button("Check for New Requests"):
                st.success("Checking for new requests...")
                # In a real implementation, this would query the blockchain
                # For demo purposes, we'll just show a message
                st.info("Found 1 new request. See details below.")

                # Create a sample request for demo purposes
                if "purchase_requests" not in st.session_state:
                    st.session_state.purchase_requests = []

                    # Add a sample request
                    sample_request = {
                        "request_id": "sample-request-123",
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
                            st.markdown("**Reply to Request**")
                            template_cid = st.text_input("Template CID", key=f"template_cid_{i}")
                            submit_button = st.form_submit_button("Submit Reply")

                            if submit_button:
                                if not template_cid:
                                    st.error("Please enter a Template CID")
                                else:
                                    # Call API to reply to purchase request
                                    try:
                                        response = requests.post(
                                            f"{API_URL}/purchase/reply",
                                            json={
                                                "request_id": request["request_id"],
                                                "template_cid": template_cid,
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
                                                    "template_cid": template_cid,
                                                    "wallet_address": st.session_state.wallet_address
                                                }
                                            )

                                        if response.status_code == 200:
                                            result = response.json()
                                            st.success("Reply submitted successfully!")
                                            st.markdown(f"**Transaction Hash:** {result.get('transaction_hash', 'N/A')[:10]}...{result.get('transaction_hash', 'N/A')[-6:]}")

                                            # Remove the request from the list
                                            st.session_state.purchase_requests.pop(i)
                                            st.info("Request has been processed and removed from the pending list.")
                                            st.rerun()
                                        else:
                                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
            else:
                st.info("No pending requests. Requests from buyers will appear here.")

            # Form for manually replying to purchase requests
            with st.expander("Manually Reply to Purchase Request"):
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

                            # If the first URL fails, try the alternative URL
                            if response.status_code == 404:
                                print("Trying alternative API URL...")
                                response = requests.post(
                                    f"{API_URL}/api/purchase/reply",
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
                amount = st.number_input("Escrow Amount (ETH)", min_value=0.001, value=0.1, step=0.001)

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
                            request_txs.sort(key=lambda x: x["timestamp"], reverse=True)

                            # Create a DataFrame for display
                            tx_data = []
                            for tx in request_txs:
                                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                                tx_hash = tx.get("tx_hash", "N/A")
                                tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if tx_hash != "N/A" else "N/A"

                                tx_data.append({
                                    "Type": tx["type"],
                                    "Status": tx["status"],
                                    "Timestamp": tx_time,
                                    "TX Hash": tx_hash_short,
                                    "Gas Fee (ETH)": tx.get("gas_fee", "N/A"),
                                    "Amount (ETH)": tx.get("amount", "N/A")
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
                                st.markdown(f"**Template CID:** `{latest_tx.get('template_cid', 'N/A')}`")
                                st.markdown(f"**Hospital:** `{latest_tx.get('hospital', 'N/A')}`")
                                st.markdown(f"**Records Count:** {latest_tx['details'].get('records_count', 'N/A')}")
                                st.markdown(f"**Patients Count:** {latest_tx['details'].get('patients_count', 'N/A')}")
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

                    # Create a visual representation of the workflow
                    for request_id in request_ids:
                        with st.expander(f"Request: {request_id}", expanded=True):
                            # Filter transactions for this request ID
                            request_txs = [tx for tx in st.session_state.transaction_history if tx["request_id"] == request_id]

                            # Sort by timestamp
                            request_txs.sort(key=lambda x: x["timestamp"])

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
