import logging
import unittest

from pygroupsig import crl, gml, group, key, load_library, signature
from pygroupsig.definitions import SCHEMES

for scheme in SCHEMES:
    logging.getLogger(f"pygroupsig.schemes.{scheme}").setLevel(logging.CRITICAL)


class SetUpMixin:
    scheme: str

    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)()
        self.group.setup()


class AddMemberMixin:
    scheme: str

    def addMember(self):
        memkey = key(self.scheme, "member")()
        msg2 = None
        seq = self.group.join_seq()
        for _ in range(0, seq + 1, 2):
            msg1 = self.group.join_mgr(msg2)
            msg2 = self.group.join_mem(msg1, memkey)
        return memkey

    def addMemberIsolated(self):
        gs = group(self.scheme)()
        gs.setup()
        memkey = key(self.scheme, "member")()
        msg2 = None
        seq = gs.join_seq()
        for _ in range(0, seq + 1, 2):
            msg1 = gs.join_mgr(msg2)
            msg2 = gs.join_mem(msg1, memkey)
        return gs, memkey


# TODO: Different group manager and members
class TestBase(AddMemberMixin):
    scheme: str

    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)()

    def test_1a_initialGroupState(self):
        for v in vars(self.group.group_key):
            self.assertTrue(getattr(self.group.group_key, v).is_zero())
        for v in vars(self.group.manager_key):
            self.assertTrue(getattr(self.group.manager_key, v).is_zero())
        if hasattr(self.group, "gml"):
            self.assertFalse(self.group.gml)
        if hasattr(self.group, "crl"):
            self.assertFalse(self.group.crl)

    def test_1b_groupStateAfterSetup(self):
        self.group.setup()
        for v in vars(self.group.group_key):
            self.assertFalse(getattr(self.group.group_key, v).is_zero())
        for v in vars(self.group.manager_key):
            self.assertFalse(getattr(self.group.manager_key, v).is_zero())

    def test_1c_initialMemKeyState(self):
        memkey = key(self.scheme, "member")()
        for v in vars(memkey):
            el = getattr(memkey, v)
            if isinstance(el, int):
                self.assertEqual(el, -1)
            elif isinstance(el, str):
                self.assertEqual(el, "")
            else:
                self.assertTrue(getattr(memkey, v).is_zero())

    def test_1d_memKeyStateAfterSetup(self):
        self.group.setup()
        memkey = key(self.scheme, "member")()
        msg2 = None
        seq = self.group.join_seq()
        for _ in range(0, seq + 1, 2):
            msg1 = self.group.join_mgr(msg2)
            self.assertEqual(msg1["status"], "success")
            msg2 = self.group.join_mem(msg1, memkey)
            self.assertEqual(msg2["status"], "success")
        for v in vars(memkey):
            el = getattr(memkey, v)
            if isinstance(el, int):
                self.assertNotEqual(el, -1)
            elif isinstance(el, str):
                self.assertNotEqual(el, "")
            else:
                self.assertFalse(getattr(memkey, v).is_zero())
        if hasattr(self.group, "gml"):
            self.assertEqual(len(self.group.gml), 1)

    def test_1e_gml(self):
        self.group.setup()
        if hasattr(self.group, "gml"):
            n = 10
            memkeys = [self.addMember() for _ in range(n)]
            self.assertEqual(len(self.group.gml), len(memkeys))
        else:
            raise unittest.SkipTest("Requires GML")

    def test_1f_validSignature(self):
        self.group.setup()
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        self.assertEqual(sig_msg["status"], "success")
        ver_msg = self.group.verify(text, sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "success")

    def test_1g_invalidSignatureMessage(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        ver_msg = self.group.verify("World hello!", sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "fail")

    def test_1h_invalidSignature(self):
        self.group.setup()
        gs, memkey = self.addMemberIsolated()
        text = "Hello world!"
        sig_msg = gs.sign(text, memkey)
        ver_msg = self.group.verify(text, sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "fail")


class TestOpen:
    def test_2a_openSignature(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        self.assertEqual(open_msg["status"], "success")
        self.assertNotEqual(open_msg["id"], "")

    def test_2b_openInvalidSignature(self):
        self.group.setup()
        gs, memkey = self.addMemberIsolated()
        sig_msg = gs.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        self.assertEqual(open_msg["status"], "fail")


class TestOpenVerify:
    def test_2c_openAndVerification(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        openver_msg = self.group.open_verify(
            sig_msg["signature"], open_msg["proof"]
        )
        self.assertEqual(openver_msg["status"], "success")

    def test_2d_openAndVerificationInvalidProof(self):
        self.group.setup()
        gs, memkey = self.addMemberIsolated()
        sig_msg = gs.sign("Hello world!", memkey)
        open_msg = gs.open(sig_msg["signature"])
        openver_msg = self.group.open_verify(
            sig_msg["signature"], open_msg["proof"]
        )
        self.assertEqual(openver_msg["status"], "fail")


class TestReveal(AddMemberMixin, SetUpMixin):
    def test_3a_reveal(self):
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        rev_msg = self.group.reveal(open_msg["id"])
        self.assertEqual(rev_msg["status"], "success")

    def test_3b_revealInvalidSignature(self):
        gs, memkey = self.addMemberIsolated()
        sig_msg = gs.sign("Hello world!", memkey)
        open_msg = gs.open(sig_msg["signature"])
        rev_msg = self.group.reveal(open_msg["id"])
        self.assertEqual(rev_msg["status"], "fail")

    def test_3c_crl(self):
        n = 10
        for _ in range(n):
            memkey = self.addMember()
            sig_msg = self.group.sign("Hello world!", memkey)
            open_msg = self.group.open(sig_msg["signature"])
            self.group.reveal(open_msg["id"])
        self.assertEqual(len(self.group.crl), n)

    def test_3d_trace(self):
        n = 3
        memkeys = []
        sigs = []
        for i in range(n):
            memkeys.append(self.addMember())
            sig_msg = self.group.sign(f"Hello world {i}!", memkeys[-1])
            sigs.append(sig_msg["signature"])
        open_msg = self.group.open(sigs[0])
        self.group.reveal(open_msg["id"])
        trace_msg = self.group.trace(sigs[0])
        self.assertEqual(trace_msg["status"], "success")
        self.assertTrue(trace_msg["revoked"])
        trace2_msg = self.group.trace(sigs[-1])
        self.assertEqual(trace2_msg["status"], "fail")

    def test_3e_proveEqualityAndVerification(self):
        n = 3
        memkey = self.addMember()
        sigs = []
        for i in range(n):
            sig_msg = self.group.sign(f"Hello world {i}!", memkey)
            sigs.append(sig_msg["signature"])
        proveq_msg = self.group.prove_equality(sigs, memkey)
        self.assertEqual(proveq_msg["status"], "success")
        proveqver_msg = self.group.prove_equality_verify(
            sigs, proveq_msg["proof"]
        )
        self.assertEqual(proveqver_msg["status"], "success")

    def test_3f_proveEqualityAndVerificationInvalidSignature(self):
        n = 3
        memkeys = [self.addMember() for _ in range(n)]
        sigs = []
        for i in range(n):
            sig_msg = self.group.sign(f"Hello world {i}!", memkeys[i % 2])
            sigs.append(sig_msg["signature"])
        proveq_msg = self.group.prove_equality(sigs, memkeys[0])
        self.assertEqual(proveq_msg["status"], "success")
        proveqver_msg = self.group.prove_equality_verify(
            sigs, proveq_msg["proof"]
        )
        self.assertEqual(proveqver_msg["status"], "fail")

    def test_3g_claimAndVerification(self):
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        claim_msg = self.group.claim(sig_msg["signature"], memkey)
        self.assertEqual(claim_msg["status"], "success")
        claimver_msg = self.group.claim_verify(
            sig_msg["signature"], claim_msg["proof"]
        )
        self.assertEqual(claimver_msg["status"], "success")


class TestBlind(AddMemberMixin, SetUpMixin):
    def test_3a_blind(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        self.assertEqual(blind_msg["status"], "success")

    def test_3b_convert(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        blind1_msg = self.group.blind(text1, sig1_msg["signature"])
        bkey = key(self.scheme, "blind").from_b64(blind1_msg["blind_key"])
        blind2_msg = self.group.blind(
            text2, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind1_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        self.assertEqual(conv_msg["status"], "success")

    def test_3c_unblind(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "Word hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        blind1_msg = self.group.blind(text1, sig1_msg["signature"])
        bkey = key(self.scheme, "blind").from_b64(blind1_msg["blind_key"])
        blind2_msg = self.group.blind(
            text2, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind1_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        conv_sigs = conv_msg["converted_signatures"]
        nyms = []
        for csig in conv_sigs:
            unblind_msg = self.group.unblind(csig, bkey)
            self.assertEqual(unblind_msg["status"], "success")
            nyms.append(unblind_msg["nym"])
        self.assertEqual(nyms[0], nyms[1])

    def test_3d_blindPipelineDifferentMember(self):
        memkey1 = self.addMember()
        memkey2 = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey1)
        sig2_msg = self.group.sign(text2, memkey2)
        blind1_msg = self.group.blind(text1, sig1_msg["signature"])
        bkey = key(self.scheme, "blind").from_b64(blind1_msg["blind_key"])
        blind2_msg = self.group.blind(
            text2, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind1_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        conv_sigs = conv_msg["converted_signatures"]
        nyms = []
        for csig in conv_sigs:
            unblind_msg = self.group.unblind(csig, bkey)
            nyms.append(unblind_msg["nym"])
        self.assertNotEqual(nyms[0], nyms[1])

    def test_3e_blindPipelineNonTransitive(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        blind1_msg = self.group.blind(text1, sig1_msg["signature"])
        bkey = key(self.scheme, "blind").from_b64(blind1_msg["blind_key"])
        blind2_msg = self.group.blind(
            text2, sig2_msg["signature"], blind_key=bkey
        )
        conv1_msg = self.group.convert(
            [blind1_msg["blind_signature"]], bkey.public()
        )
        conv2_msg = self.group.convert(
            [blind2_msg["blind_signature"]], bkey.public()
        )
        unblind1_msg = self.group.unblind(
            conv1_msg["converted_signatures"][0], bkey
        )
        unblind2_msg = self.group.unblind(
            conv2_msg["converted_signatures"][0], bkey
        )
        self.assertNotEqual(unblind1_msg["nym"], unblind2_msg["nym"])


class TestLink(AddMemberMixin, SetUpMixin):
    def test_3a_identify(self):
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        iden_msg = self.group.identify(sig_msg["signature"], memkey)
        self.assertEqual(iden_msg["status"], "success")

    def test_3b_identifyDifferentScope(self):
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        iden_msg = self.group.identify(
            sig_msg["signature"], memkey, scope="fed"
        )
        self.assertEqual(iden_msg["status"], "fail")

    def test_3c_link(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        iden_msg = self.group.link(
            "password",
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
        )
        self.assertEqual(iden_msg["status"], "success")

    def test_3d_linkDifferentScope(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        iden_msg = self.group.link(
            "password",
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
            scope="fed",
        )
        self.assertEqual(iden_msg["status"], "fail")

    def test_3e_linkDifferentUser(self):
        memkey = self.addMember()
        gs, memkey2 = self.addMemberIsolated()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = gs.sign(text2, memkey)
        passw = "password"
        iden_msg = self.group.link(
            passw,
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
        )
        self.assertEqual(iden_msg["status"], "fail")

    def test_3f_linkAndVerification(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        passw = "password"
        iden_msg = self.group.link(
            passw,
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
        )
        idenver_msg = self.group.link_verify(
            passw,
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            iden_msg["proof"],
        )
        self.assertEqual(idenver_msg["status"], "success")

    def test_3g_linkAndVerificationDifferentMessage(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        iden_msg = self.group.link(
            "password",
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
        )
        idenver_msg = self.group.link_verify(
            "password2",
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            iden_msg["proof"],
        )
        self.assertEqual(idenver_msg["status"], "fail")

    def test_3h_linkAndVerificationDifferentScope(self):
        memkey = self.addMember()
        text1 = "Hello world!"
        text2 = "World hello!"
        sig1_msg = self.group.sign(text1, memkey)
        sig2_msg = self.group.sign(text2, memkey)
        passw = "password"
        iden_msg = self.group.link(
            passw,
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            memkey,
        )
        idenver_msg = self.group.link_verify(
            passw,
            [text1, text2],
            [sig1_msg["signature"], sig2_msg["signature"]],
            iden_msg["proof"],
            scope="fed",
        )
        self.assertEqual(idenver_msg["status"], "fail")


class TestLinkSeq(AddMemberMixin, SetUpMixin):
    def test_3i_seqlinkAndVerification(self):
        memkey = self.addMember()
        text = "Hello world!"
        text2 = "World hello!"
        text3 = "! hello world"
        sig1_msg = self.group.sign(text, memkey, state=0)
        sig2_msg = self.group.sign(text2, memkey, state=1)
        sig3_msg = self.group.sign(text3, memkey, state=2)
        passw = "password"
        iden_msg = self.group.seqlink(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            memkey,
        )
        idenver_msg = self.group.seqlink_verify(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            iden_msg["proof"],
        )
        self.assertEqual(idenver_msg["status"], "success")

    def test_3j_seqlinkAndVerificationWrongOrderSwap(self):
        memkey = self.addMember()
        text = "Hello world!"
        text2 = "World hello!"
        text3 = "! hello world"
        sig1_msg = self.group.sign(text, memkey, state=0)
        sig2_msg = self.group.sign(text2, memkey, state=2)
        sig3_msg = self.group.sign(text3, memkey, state=1)
        passw = "password"
        iden_msg = self.group.seqlink(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            memkey,
        )
        idenver_msg = self.group.seqlink_verify(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            iden_msg["proof"],
        )
        self.assertEqual(idenver_msg["status"], "fail")

    def test_3k_seqlinkAndVerificationWrongOrderSkip(self):
        memkey = self.addMember()
        text = "Hello world!"
        text2 = "World hello!"
        text3 = "! hello world"
        sig1_msg = self.group.sign(text, memkey, state=0)
        sig2_msg = self.group.sign(text2, memkey, state=1)
        sig3_msg = self.group.sign(text3, memkey, state=3)
        passw = "password"
        iden_msg = self.group.seqlink(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            memkey,
        )
        idenver_msg = self.group.seqlink_verify(
            passw,
            [text, text2, text3],
            [
                sig1_msg["signature"],
                sig2_msg["signature"],
                sig3_msg["signature"],
            ],
            iden_msg["proof"],
        )
        self.assertEqual(idenver_msg["status"], "fail")


class TestBaseExportImport(AddMemberMixin, SetUpMixin):
    def test_4a_exportImportGroupKey(self):
        grpkey_b64 = self.group.group_key.to_b64()
        grpkey1 = key(self.scheme, "group")()
        grpkey1.set_b64(grpkey_b64)
        self.assertEqual(str(grpkey1), str(self.group.group_key))
        grpkey2 = key(self.scheme, "group").from_b64(grpkey_b64)
        self.assertEqual(str(grpkey2), str(self.group.group_key))

    def test_4b_exportImportManagerKey(self):
        mgrkey_b64 = self.group.manager_key.to_b64()
        mgrkey1 = key(self.scheme, "manager")()
        mgrkey1.set_b64(mgrkey_b64)
        self.assertEqual(str(mgrkey1), str(self.group.manager_key))
        mgrkey2 = key(self.scheme, "manager").from_b64(mgrkey_b64)
        self.assertEqual(str(mgrkey2), str(self.group.manager_key))

    def test_4c_exportImportMemberKey(self):
        memkey = self.addMember()
        memkey_b64 = memkey.to_b64()
        memkey1 = key(self.scheme, "member")()
        memkey1.set_b64(memkey_b64)
        self.assertEqual(str(memkey1), str(memkey))
        memkey2 = key(self.scheme, "member").from_b64(memkey_b64)
        self.assertEqual(str(memkey2), str(memkey))

    def test_4d_exportImportSignature(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig1 = signature(self.scheme)()
        sig1.set_b64(sig_msg["signature"])
        ver1_msg = self.group.verify(text, sig1.to_b64())
        self.assertEqual(ver1_msg["status"], "success")
        sig2 = signature(self.scheme).from_b64(sig_msg["signature"])
        ver2_msg = self.group.verify(text, sig2.to_b64())
        self.assertEqual(ver2_msg["status"], "success")

    def test_4e_exportImportGML(self):
        if hasattr(self.group, "gml"):
            self.addMember()
            self.addMember()
            gml_b64 = self.group.gml.to_b64()
            gml1 = gml()
            gml1.set_b64(gml_b64)
            self.assertEqual(str(gml1), str(self.group.gml))
            gml2 = gml.from_b64(gml_b64)
            self.assertEqual(str(gml2), str(self.group.gml))
        else:
            raise unittest.SkipTest("Requires GML")

    def test_4f_exportImportCRL(self):
        if hasattr(self.group, "crl"):
            memkey1 = self.addMember()
            memkey2 = self.addMember()
            sig1_msg = self.group.sign("Hello world!", memkey1)
            open2_msg = self.group.open(sig1_msg["signature"])
            self.group.reveal(open2_msg["id"])
            sig2_msg = self.group.sign("World hello!", memkey2)
            open2_msg = self.group.open(sig2_msg["signature"])
            self.group.reveal(open2_msg["id"])
            crl_b64 = self.group.crl.to_b64()
            crl1 = crl()
            crl1.set_b64(crl_b64)
            self.assertEqual(str(crl1), str(self.group.crl))
            crl2 = gml.from_b64(crl_b64)
            self.assertEqual(str(crl2), str(self.group.crl))
        else:
            raise unittest.SkipTest("Requires CRL")


class TestBlindExportImport:
    def test_4f_exportImportBlindKey(self):
        from pygroupsig.schemes.gl19 import BlindKey

        blindkey = BlindKey.from_random(self.group.group_key)
        blindkey_b64 = blindkey.to_b64()
        blindkey1 = key(self.scheme, "blind")()
        blindkey1.set_b64(blindkey_b64)
        self.assertEqual(str(blindkey1), str(blindkey))
        blindkey2 = key(self.scheme, "blind").from_b64(blindkey_b64)
        self.assertEqual(str(blindkey2), str(blindkey))
