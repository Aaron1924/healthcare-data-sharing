import logging

from pygroupsig import group, key, load_library

if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s|%(name)s: %(message)s", level=logging.ERROR
    )
    load_library()
    sch = "gl19"
    # Group object for the manager
    gs = group(sch)
    gs.setup()
    gk_b64 = gs.grpkey.to_b64()

    # Group object for the member1
    gsm = group(sch)
    gsm.grpkey.set_b64(gk_b64)
    mk = key(sch, "member")

    mem1_msg1 = gs.join_mgr()
    mem1_msg2 = gsm.join_mem(mem1_msg1, mk)
    mem1_msg3 = gs.join_mgr(mem1_msg2)
    mem1_msg4 = gsm.join_mem(mem1_msg3, mk)

    text = "Hello world!"

    sig_msg = gsm.sign(text, mk)
    sig2_msg = gsm.sign(text, mk)
    # sig_msg2 = gsm.sign("World hello!", mk)
    # sig = signature(b64=sig_msg["signature"])
    # print("signature: ", sig)
    # res = gsm.verify(text, sig_msg["signature"])
    # print(res)

    blind_msg = gsm.blind(text, sig_msg["signature"])
    bkey = key(b64=blind_msg["blind_key"])
    blind2_msg = gsm.blind(text, sig2_msg["signature"], blind_key=bkey)

    conv_msg = gs.convert(
        [blind_msg["blind_signature"], blind2_msg["blind_signature"]],
        bkey.public(),
    )
    conv_sigs = conv_msg["converted_signatures"]
    nyms = []
    for csig in conv_sigs:
        unblind_msg = gsm.unblind(csig, bkey)
        nyms.append(unblind_msg["nym"])
    if nyms[0] == nyms[1]:
        print("Good")
