from pygroupsig import load_library, Scheme, Key
from pygroupsig.pairings.mcl import Fp

if __name__ == "__main__":
    load_library()
    gs = Scheme("klap20")
    gs.setup()
    msg1 = gs.join_mgr(0)
    print(msg1)
    msg2 = gs.join_mem(1, msg1)
    print(msg2)
    msg3 = gs.join_mgr(2, msg2)
    print(msg3)
    msg4 = gs.join_mem(3, msg3)
    print(msg4)
    sig = gs.sign("Hello world!")
    print(sig)
    res = gs.verify("Hello world!", sig["signature"])
    print(res)
