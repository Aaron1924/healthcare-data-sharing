#!/usr/bin/env python3
"""
Key generation script using CPY06 scheme from pygroupsig.
This scheme supports both group and revocation managers.
"""

from pygroupsig import group, key
import os
import json
import base64

# Create output directory
os.makedirs("keys", exist_ok=True)

print("Generating keys using CPY06 scheme...")

# Step 1: Initialize the group with CPY06 scheme
g = group("cpy06")()  # Note: `group` function returns a class, not an instance
g.setup()

# Step 2: Get and save the group public key
gk_b64 = g.group_key.to_b64()
print(f"\nGroup public key generated: {gk_b64[:20]}...")

# Save group public key
with open("keys/group_public_key.b64", "w") as f:
    f.write(gk_b64)
print("Group public key saved to keys/group_public_key.b64")

# Step 3: Extract and save the group manager's secret key
print("\nExtracting group manager's secret key...")
# For CPY06, we need to save the components separately
gm_key = {
    "xi1": str(g.manager_key.xi1),
    "xi2": str(g.manager_key.xi2),
    "gamma": str(g.manager_key.gamma)
}

# Save group manager key
with open("keys/group_manager_key.json", "w") as f:
    json.dump(gm_key, f, indent=2)
print("Group manager key saved to keys/group_manager_key.json")

# Step 4: Extract and save the revocation manager's secret key
print("\nExtracting revocation manager's secret key...")
rm_key = {
    "xi1": str(g.revocation_manager_key.xi1),
    "xi2": str(g.revocation_manager_key.xi2)
}

# Save revocation manager key
with open("keys/revocation_manager_key.json", "w") as f:
    json.dump(rm_key, f, indent=2)
print("Revocation manager key saved to keys/revocation_manager_key.json")

# Step 5: Create client-side group for doctor
print("\nCreating client-side group for doctor...")
gm = group("cpy06")()
gm.group_key.set_b64(gk_b64)

# Create a member key for the doctor
print("Creating doctor's member key...")
mk = key("cpy06", "member")()

# Execute the join protocol
print("Executing join protocol...")
msg2 = None
seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = g.join_mgr(msg2)  # Group manager side
    msg2 = gm.join_mem(msg1, mk)  # Member (doctor) side

# Save doctor's member key
with open("keys/doctor_member_key.b64", "w") as f:
    f.write(mk.to_b64())
print("Doctor's member key saved to keys/doctor_member_key.b64")

# Step 6: Test signing
print("\nTesting signing...")
test_message = "Test medical record"
s_msg = gm.sign(test_message, mk)
print(f"Signature created")

# Test verification
v_result = gm.verify(test_message, s_msg["signature"])
print(f"Verification result: {v_result}")

# Step 7: Test opening (tracing)
print("\nTesting opening (tracing)...")

# Group manager partial opening
partial_g_result = g.open(s_msg["signature"])
print(f"Group Manager partial opening computed")

# Revocation manager partial opening
partial_r_result = g.open(s_msg["signature"], group_manager_partial=partial_g_result["partial_g"])
print(f"Revocation Manager partial opening computed")

# Full opening
full_open_result = g.open(
    s_msg["signature"],
    group_manager_partial=partial_g_result["partial_g"],
    revocation_manager_partial=partial_r_result["partial_r"]
)
print(f"Full opening result computed")

# Save test signature
with open("keys/test_signature.json", "w") as f:
    json.dump({
        "message": test_message,
        "signature": str(s_msg["signature"]),
        "partial_g": str(partial_g_result["partial_g"]),
        "partial_r": str(partial_r_result["partial_r"]),
        "full_open": str(full_open_result)
    }, f, indent=2)
print("Test signature saved to keys/test_signature.json")

print("\nAll keys generated and saved successfully!")
print("Files created:")
print("  - keys/group_public_key.b64")
print("  - keys/group_manager_key.json")
print("  - keys/revocation_manager_key.json")
print("  - keys/doctor_member_key.b64")
print("  - keys/test_signature.json")
