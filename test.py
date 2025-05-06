from pygroupsig import group,key

## Two variants

# Method1
g = group("bbs04")() # Note: `group` function returns a class, not an instance
# Method2
# g = GroupBBS04()

g.setup()
gk_b64 = g.group_key.to_b64()

# Client side: create a group to use join protocol; you need to set the group_key (public)
gm = group("bbs04")()
gm.group_key.set_b64(gk_b64)

# Method 1
mk = key("bbs04", "member")()

# Method 2
# mk = MemberKeyBBS04()
# Test join protocol that take into account each scheme needs
msg2 = None
seq = gm.join_seq()
for _ in range(0, seq + 1, 2):
    msg1 = g.join_mgr(msg2) # Group manager side
    msg2 = gm.join_mem(msg1, mk) # Member side

s_msg = gm.sign("Hello world!", mk)
print(s_msg["signature"])
v_msg = gm.verify("Hello world!", s_msg["signature"])
print(v_msg)


