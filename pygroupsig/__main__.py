import logging

from pygroupsig import group, key, load_library

if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s|%(name)s: %(message)s", level=logging.ERROR
    )
    load_library()
    sch = "cpy06"
    # Group object for the manager
    gs = group(sch)
    gs.setup()
    gk_b64 = gs.grpkey.to_b64()

    # Group object for the member1
    gsm = group(sch)
    gsm.grpkey.set_b64(gk_b64)
    mk = key(sch, "member")

    mem1_msg1 = gs.join_mgr(0)
    # print(mem1_msg1)c
    mem1_msg2 = gsm.join_mem(1, mem1_msg1, mk)
    # print(mem1_msg2)
    mem1_msg3 = gs.join_mgr(2, mem1_msg2)
    # print(mem1_msg3)
    mem1_msg4 = gsm.join_mem(3, mem1_msg3, mk)
    # breakpoint()
    # gml_b64 = gs.gml.to_b64()
    # from pygroupsig.helpers import GML
    # asd = GML.from_b64(gml_b64)
    # print(mem1_msg4)
    # print("grpkey: ", gs.grpkey)
    # print("mgrkey: ", gs.mgrkey)
    # print("memkey: ", mk)

    sig_msg = gsm.sign("Hello world!", mk)
    sig_msg2 = gsm.sign("World hello!", mk)
    # sig = signature(b64=sig_msg["signature"])
    # print("signature: ", sig)
    # res = gsm.verify("Hello world!", sig_msg["signature"])
    # print(res)
    prv_msg = gsm.prove_equality(
        [sig_msg["signature"], sig_msg2["signature"]], mk
    )
    print(
        gsm.prove_equality_verify(
            [sig_msg["signature"], sig_msg2["signature"]], prv_msg["proof"]
        )
    )

    cla_msg = gsm.claim(sig_msg["signature"], mk)
    print(gsm.claim_verify(sig_msg["signature"], cla_msg["proof"]))

    # res_open = gs.open(sig_msg["signature"])
    # print(res_open)
    # res_reveal = gs.reveal(res_open["id"])
    # print(res_reveal)
    # res_reveal2 = gs.reveal("invalid id")
    # print(res_reveal2)
    # res_trace = gs.trace(sig_msg["signature"])
    # print(res_trace)
    # print(gs.open_verify(sig_msg["signature"], res_open["proof"]))

    # gs2 = group(sch)
    # gs2.setup()
    # gk2_b64 = gs2.grpkey.to_b64()

    # # Group object for the member2
    # gs2m = group(sch)
    # gs2m.grpkey.set_b64(gk2_b64)

    # mk2 = key(sch, "member")
    # mem2_msg1 = gs2.join_mgr(0)
    # # print(mem2_msg1)
    # mem2_msg2 = gs2m.join_mem(1, mem2_msg1, mk2)
    # # print(mem2_msg2)
    # mem2_msg3 = gs2.join_mgr(2, mem2_msg2)
    # # print(mem2_msg3)
    # mem2_msg4 = gs2m.join_mem(3, mem2_msg3, mk2)
    # # print(mem2_msg4)
    # # print("grpkey: ", gs2.grpkey)
    # # print("mgrkey: ", gs2.mgrkey)
    # # print("memkey: ", mk)

    # sig2_msg = gs2m.sign("Hello world!", mk2)
    # sig2 = signature(b64=sig2_msg["signature"])
    # # print("signature: ", sig2)
    # # res = gsm.verify("Hello world!", sig2_msg["signature"])
    # # print(res)

    # prv_msg = gsm.prove_equality([sig_msg["signature"], sig_msg2["signature"]], mk2)
    # print(gsm.prove_equality_verify([sig_msg["signature"], sig_msg2["signature"]], prv_msg["proof"]))
