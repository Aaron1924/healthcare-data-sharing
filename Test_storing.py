
import json
import os
import ipfshttpclient

from pygroupsig import group,key

from backend.data import MerkleService
from backend.roles import Patient, Doctor, GroupManager

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from typing import List, Dict, Optional, Tuple


Hospitalgroup = group("cpy06")()

Hospitalgroup.setup()
gk_b64 = Hospitalgroup.group_key.to_b64()

gm = group("cpy06")()
gm.group_key.set_b64(gk_b64)
doctor1_key = key("cpy06", "member")()
# Simulate join process (in practice, run group.join_mgr and group.join_mem)

msg2 = None

seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = Hospitalgroup.join_mgr(msg2)  # Group manager side
    msg2 = gm.join_mem(msg1, doctor1_key)  # Member side

#test data in dictionary
patient_data = {
    "patientID": "123",
    "date": "2025-04-18",
    "diagnosis": "Hypertension",
    "doctorID": "DOC789",
    "notes": "Patient advised to monitor blood pressure daily and start low-dose medication."
  }

HospitalInfo = "Hospital A, 123 Main St, Cityville"

merkle_Patient1 = MerkleService()
IDRecs_patient1, proofs = merkle_Patient1.create_merkle_tree(patient_data)

# print("===IDRecs_patient1===")
# print("IDRecs_patient1:", IDRecs_patient1)
# print("======")

#Encrypted record has been signed
SD = gm.sign(IDRecs_patient1, doctor1_key)
print(SD)
v_msg = gm.verify(IDRecs_patient1, SD["signature"])

partial_g_result = Hospitalgroup.open(SD["signature"])

# Step 2: Get partial opening information from Revocation Manager
partial_r_result = Hospitalgroup.open(SD["signature"], group_manager_partial=partial_g_result["partial_g"])

full_open_result = Hospitalgroup.open(
    SD["signature"],
    group_manager_partial=partial_g_result["partial_g"],
    revocation_manager_partial=partial_r_result["partial_r"]
)
print(f"Full opening result: {full_open_result}")


private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

private_key1 = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key1 = private_key.public_key()

PatientA = Patient(private_key=private_key, public_key=public_key)
HospitalAGM = GroupManager(private_key=private_key1, public_key=public_key1)

KeyERec = PatientA.generate_key()
ERecord = PatientA.encrypt_record(patient_data, KeyERec)


PatientA.upload_ipfs_records(ERecord, HospitalInfo, public_key1, KeyERec)











