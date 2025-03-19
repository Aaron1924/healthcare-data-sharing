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

> The library was tested in [mcl v2.00](https://github.com/herumi/mcl/tree/v2.00)

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

## Acknowledgement
This work was supported by the European Commission under the Horizon Europe funding
programme, as part of the project SafeHorizon (Grant Agreement 101168562).
Moreover, it was supported by the European Commission under the Horizon Europe
Programme as part of the HEROES project (Grant Agreement number 101021801)
and the European Union's Internal Security Fund as part of the ALUNA project
(Grant Agreement number 101084929). Views and opinions expressed are however
those of the author(s) only and do not necessarily reflect those of the European.
Neither the European Union nor the granting authority can be held responsible for them.

- Based on [piotrszyma/mcl-python](https://github.com/piotrszyma/mcl-python) bindings for mcl.
- Based on [herumi/mcl](https://github.com/herumi/mcl).
- Based on [spirs/libgroupsig](https://gitlab.gicp.es/spirs/libgroupsig) and [IBM/libgroupsig](https://github.com/IBM/libgroupsig)

## LICENSE
```
Copyright (c) 2024 Cybersecurity and Privacy Protection Research Group (GiCP), part of Consejo Superior de Investigaciones Científicas (CSIC). All rights reserved.
This work is licensed under the terms of the MIT license.
```
For a copy, see [LICENSE](LICENSE)
