#!/usr/bin/env python3
"""
Simple key generation script following test1.py example.
"""

from pygroupsig import group, key
import os
import json

# Create output directory
os.makedirs("keys", exist_ok=True)

# Step 1: Initialize the group with CPY06 scheme
print("Step 1: Initializing group...")
g = group("cpy06")()
g.setup()

# Step 2: Get the group public key
print("Step 2: Getting group public key...")
gk_b64 = g.group_key.to_b64()

# Save group public key
with open("keys/group_public_key.b64", "w") as f:
    f.write(gk_b64)

# Step 3: Print group manager and revocation manager keys
print("\n=== Group Manager Key ===")
print(f"xi1 (GM share): {g.manager_key.xi1}")
print(f"xi2 (GM share): {g.manager_key.xi2}")
print(f"gamma (GM share): {g.manager_key.gamma}")

print("\n=== Revocation Manager Key ===")
print(f"xi1 (RM share): {g.revocation_manager_key.xi1}")
print(f"xi2 (RM share): {g.revocation_manager_key.xi2}")

# Save manager keys as strings
with open("keys/group_manager_key.json", "w") as f:
    json.dump({
        "xi1": str(g.manager_key.xi1),
        "xi2": str(g.manager_key.xi2),
        "gamma": str(g.manager_key.gamma)
    }, f, indent=2)

with open("keys/revocation_manager_key.json", "w") as f:
    json.dump({
        "xi1": str(g.revocation_manager_key.xi1),
        "xi2": str(g.revocation_manager_key.xi2)
    }, f, indent=2)

# Step 4: Create client-side group and member key
print("\nStep 4: Creating doctor's member key...")
gm = group("cpy06")()
gm.group_key.set_b64(gk_b64)
mk = key("cpy06", "member")()

# Step 5: Execute join protocol
print("Step 5: Executing join protocol...")
msg2 = None
seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = g.join_mgr(msg2)  # Group manager side
    msg2 = gm.join_mem(msg1, mk)  # Member (doctor) side

# Save doctor's member key
with open("keys/doctor_member_key.b64", "w") as f:
    f.write(mk.to_b64())

# Step 6: Test signing
print("\nStep 6: Testing signing...")
test_message = "Test medical record"
s_msg = gm.sign(test_message, mk)
print(f"Signature: {s_msg['signature']}")

# Step 7: Test verification
print("\nStep 7: Testing verification...")
v_result = gm.verify(test_message, s_msg["signature"])
print(f"Verification result: {v_result}")

# Step 8: Test opening (tracing)
print("\nStep 8: Testing opening (tracing)...")

# Group manager partial opening
partial_g_result = g.open(s_msg["signature"])
print(f"Group Manager partial: {partial_g_result}")

# Revocation manager partial opening
partial_r_result = g.open(s_msg["signature"], group_manager_partial=partial_g_result["partial_g"])
print(f"Revocation Manager partial: {partial_r_result}")

# Full opening
full_open_result = g.open(
    s_msg["signature"],
    group_manager_partial=partial_g_result["partial_g"],
    revocation_manager_partial=partial_r_result["partial_r"]
)
print(f"Full opening result: {full_open_result}")

# Save test signature data
with open("keys/test_signature.json", "w") as f:
    json.dump({
        "message": test_message,
        "signature": str(s_msg["signature"]),
        "partial_g": str(partial_g_result["partial_g"]),
        "partial_r": str(partial_r_result["partial_r"]),
        "full_open": str(full_open_result)
    }, f, indent=2)

print("\nAll keys generated and saved successfully!")
print("Files created:")
print("  - keys/group_public_key.b64")
print("  - keys/group_manager_key.json")
print("  - keys/revocation_manager_key.json")
print("  - keys/doctor_member_key.b64")
print("  - keys/test_signature.json")
