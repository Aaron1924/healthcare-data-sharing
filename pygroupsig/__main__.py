from pygroupsig import load_library, Scheme, Key
from pygroupsig.pairings.mcl import Fp

if __name__ == "__main__":
    load_library()
    sch = "ps16"
    # Group object for the manager
    gs = Scheme(sch)
    gs.setup()
    gk_b64 = gs.grpkey.to_b64()

    # Group object for the member1
    gsm = Scheme(sch)
    gsm.grpkey.set_b64(gk_b64)
    mk = Key(sch, "member")

    mem1_msg1 = gs.join_mgr(0)
    print(mem1_msg1)
    mem1_msg2 = gsm.join_mem(1, mem1_msg1, mk)
    print(mem1_msg2)
    mem1_msg3 = gs.join_mgr(2, mem1_msg2)
    print(mem1_msg3)
    mem1_msg4 = gsm.join_mem(3, mem1_msg3, mk)
    print(mem1_msg4)

    sig = gsm.sign("Hello world!", mk)
    print(sig)
    res = gsm.verify("Hello world!", sig["signature"])
    print(res)

    gs2 = Scheme(sch)
    gs2.setup()
    gk2_b64 = gs2.grpkey.to_b64()

    # Group object for the member2
    gs2m = Scheme(sch)
    gs2m.grpkey.set_b64(gk2_b64)

    mk2 = Key(sch, "member")
    mem2_msg1 = gs2.join_mgr(0)
    print(mem2_msg1)
    mem2_msg2 = gs2m.join_mem(1, mem2_msg1, mk2)
    print(mem2_msg2)
    mem2_msg3 = gs2.join_mgr(2, mem2_msg2)
    print(mem2_msg3)
    mem2_msg4 = gs2m.join_mem(3, mem2_msg3, mk2)
    print(mem2_msg4)

    sig2 = gs2m.sign("Hello world!", mk2)
    print(sig2)
    res = gsm.verify("Hello world!", sig2["signature"])
    print(res)
