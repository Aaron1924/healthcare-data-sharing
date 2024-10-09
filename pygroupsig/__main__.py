from pygroupsig import load_library, Scheme, Key
from pygroupsig.pairings.mcl import Fp

if __name__ == "__main__":
    load_library()
    breakpoint()
    f = Fp()
    f.set_random()
    g = Fp()
    g.set_random()
    gs = Scheme("klap20")
    gs.setup()
    msg1 = gs.join_mgr(0)
    msg2 = gs.join_mem(1, msg1)
    msg3 = gs.join_mgr(2, msg2)
    breakpoint()
    msg4 = gs.join_mem(3, msg3)
