# pygroupsig

Welcome to _**pygroupsig**_, an extensible library for group signatures. Below,
you can find basic information about how to use the library.

## Compilation

This library has been developed from scratch in Python _except_ for **mcl**.
We have built a wrapper around the original [mcl](https://github.com/herumi/mcl)
library written in C/C++ using Python ctypes.

> The library has type hints to ease the development of new schemes. If you encounter 
> any errors or have suggestions for improvements, please feel free to open a PR or 
> an issue.

To build **mcl**, run the following commands.

```bash
git clone https://github.com/herumi/mcl.git
cd mcl
cmake -B build .
make -C build
```

You need to export an environment variable, `MCL_LIB_PATH`, pointing to the **lib** folder 
```bash
export MCL_LIB_PATH=$PWD/mcl/build/lib
```

## Usage
You can instantiate the different schemes using the `group` class factory or by directly 
using the specific class for each scheme:

```python
from pygroupsig import group, GroupBBS04, key, MemberKeyBBS04

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
v_msg = gm.verify("Hello world!", s_msg["signature"])
```

The functions `setup`, `join_mgr`, `join_mem`, `sign` and `verify` are common to all 
schemes. Some schemes also implement additional functionalities:

### BBS04
- open

### PS16
- open
- open_verify

### CPY06
- open
- reveal
- trace
- prove_equality
- prove_equality_verify
- claim
- claim_verify

### KLAP20
- open
- open_verify

### GL19
- blind
- convert
- unblind

### DL21
- identify
- link
- link_verify

### DL21SEQ
- identify
- link
- link_verify
- seqlink
- seqlink_verify

## Tests
Run the following command to execute the tests:

```bash
python -m unittest
```