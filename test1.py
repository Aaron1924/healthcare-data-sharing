from pygroupsig import group,key
g = group("cpy06")()
g.setup()

gk_b64 = g.group_key.to_b64()

#client side
gm = group("cpy06")()
gm.group_key.set_b64(gk_b64)
mk = key("cpy06", "member")()

#join 
msg2 = None
seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = g.join_mgr(msg2) # Group manager side
    msg2 = gm.join_mem(msg1, mk) # Member side

s_msg = gm.sign("Hello world!", mk)
print(s_msg)
v_msg = gm.verify("Hello world!", s_msg["signature"])
#open 
# print("\n=== Revocation Manager Key ===")
# print(f"xi1 (RM share): {g.revocation_manager_key .xi1}")
# print(f"xi2 (RM share): {g.revocation_manager_key .xi2}")

# print("\n=== Group Manager Key ===")
# print(f"xi1 (GM share): {g.manager_key .xi1}")
# print(f"xi2 (GM share): {g.manager_key .xi2}")
# print(f"xi3 (GM share): {g.manager_key .gamma}")

partial_g_result = g.open(s_msg["signature"])
print(f"Group Manager partial: {partial_g_result}")

# Step 2: Get partial opening information from Revocation Manager
partial_r_result = g.open(s_msg["signature"], group_manager_partial=partial_g_result["partial_g"])
print(f"Revocation Manager partial: {partial_r_result}")

# Step 3: Combine the partial results to fully open the signature
full_open_result = g.open(
    s_msg["signature"],
    group_manager_partial=partial_g_result["partial_g"],
    revocation_manager_partial=partial_r_result["partial_r"]
)
print(f"Full opening result: {full_open_result}")



