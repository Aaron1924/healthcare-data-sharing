import logging
import unittest

from pygroupsig import group, key, load_library, signature
from pygroupsig.helpers import GML


class SetUpMixin:
    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)
        self.group.setup()


class AddMemberMixin:
    def addMember(self):
        memkey = key(self.scheme, "member")
        msg1 = self.group.join_mgr()
        msg2 = self.group.join_mem(msg1, memkey)
        msg3 = self.group.join_mgr(msg2)
        _ = self.group.join_mem(msg3, memkey)
        return memkey

    def addMemberIsolated(self):
        gs = group(self.scheme)
        gs.setup()
        memkey = key(self.scheme, "member")
        msg1 = gs.join_mgr()
        msg2 = gs.join_mem(msg1, memkey)
        msg3 = gs.join_mgr(msg2)
        _ = gs.join_mem(msg3, memkey)
        return gs, memkey


class AddMember2Mixin:
    def addMember(self):
        memkey = key(self.scheme, "member")
        msg1 = self.group.join_mgr()
        _ = self.group.join_mem(msg1, memkey)
        return memkey

    def addMemberIsolated(self):
        gs = group(self.scheme)
        gs.setup()
        memkey = key(self.scheme, "member")
        msg1 = gs.join_mgr()
        _ = gs.join_mem(msg1, memkey)
        return gs, memkey


class TestAddMember2:
    def test_1d_memKeyStateAfterSetup(self):
        self.group.setup()
        memkey = key(self.scheme, "member")
        msg1 = self.group.join_mgr()
        self.assertEqual(msg1["status"], "success")
        msg2 = self.group.join_mem(msg1, memkey)
        self.assertEqual(msg2["status"], "success")
        for v in vars(memkey):
            self.assertFalse(getattr(memkey, v).is_zero())
        if hasattr(self.group, "gml"):
            self.assertEqual(len(self.group.gml), 1)


# TODO: Different group manager and members
class TestBase(AddMemberMixin):
    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)

    def test_1a_initialGroupState(self):
        for v in vars(self.group.grpkey):
            self.assertTrue(getattr(self.group.grpkey, v).is_zero())
        for v in vars(self.group.mgrkey):
            self.assertTrue(getattr(self.group.mgrkey, v).is_zero())
        if hasattr(self.group, "gml"):
            self.assertFalse(self.group.gml)
        if hasattr(self.group, "crl"):
            self.assertFalse(self.group.crl)

    def test_1b_groupStateAfterSetup(self):
        self.group.setup()
        for v in vars(self.group.grpkey):
            self.assertFalse(getattr(self.group.grpkey, v).is_zero())
        for v in vars(self.group.mgrkey):
            self.assertFalse(getattr(self.group.mgrkey, v).is_zero())

    def test_1c_initialMemKeyState(self):
        memkey = key(self.scheme, "member")
        for v in vars(memkey):
            el = getattr(memkey, v)
            if isinstance(el, int):
                self.assertEqual(el, -1)
            else:
                self.assertTrue(getattr(memkey, v).is_zero())

    def test_1d_memKeyStateAfterSetup(self):
        self.group.setup()
        memkey = key(self.scheme, "member")
        msg1 = self.group.join_mgr()
        self.assertEqual(msg1["status"], "success")
        msg2 = self.group.join_mem(msg1, memkey)
        self.assertEqual(msg2["status"], "success")
        msg3 = self.group.join_mgr(msg2)
        self.assertEqual(msg3["status"], "success")
        msg4 = self.group.join_mem(msg3, memkey)
        self.assertEqual(msg4["status"], "success")
        for v in vars(memkey):
            el = getattr(memkey, v)
            if isinstance(el, int):
                self.assertNotEqual(el, -1)
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
        logging.getLogger(f"pygroupsig.schemes.{self.scheme}").setLevel(
            logging.CRITICAL
        )
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        ver_msg = self.group.verify("World hello!", sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "fail")

    def test_1h_invalidSignature(self):
        logging.getLogger(f"pygroupsig.schemes.{self.scheme}").setLevel(
            logging.CRITICAL
        )
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
            _ = self.group.reveal(open_msg["id"])
        self.assertEqual(len(self.group.crl), n)

    def test_3d_trace(self):
        n = 3
        memkeys = []
        sigs = []
        for i in range(n):
            memkeys.append(self.addMember())
            sig_msg = self.group.sign(f"Hello world! {i}", memkeys[-1])
            sigs.append(sig_msg["signature"])
        open_msg = self.group.open(sigs[0])
        _ = self.group.reveal(open_msg["id"])
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
            sig_msg = self.group.sign(f"Hello world! {i}", memkey)
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
            sig_msg = self.group.sign(f"Hello world! {i}", memkeys[i % 2])
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


class TestBlind(SetUpMixin, AddMemberMixin):
    def test_3a_blind(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        self.assertEqual(blind_msg["status"], "success")

    def test_3b_convert(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig2_msg = self.group.sign(text, memkey)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        bkey = key(b64=blind_msg["blind_key"])
        blind2_msg = self.group.blind(
            text, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        self.assertEqual(conv_msg["status"], "success")

    def test_3c_unblind(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig2_msg = self.group.sign(text, memkey)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        bkey = key(b64=blind_msg["blind_key"])
        blind2_msg = self.group.blind(
            text, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        conv_sigs = conv_msg["converted_signatures"]
        nyms = []
        for csig in conv_sigs:
            unblind_msg = self.group.unblind(csig, bkey)
            self.assertEqual(unblind_msg["status"], "success")
            nyms.append(unblind_msg["nym"])
        self.assertEqual(nyms[0], nyms[1])

    def test_3d_blindConvertUnblindDifferentMember(self):
        memkey = self.addMember()
        memkey2 = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig2_msg = self.group.sign(text, memkey2)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        bkey = key(b64=blind_msg["blind_key"])
        blind2_msg = self.group.blind(
            text, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind_msg["blind_signature"], blind2_msg["blind_signature"]],
            bkey.public(),
        )
        conv_sigs = conv_msg["converted_signatures"]
        nyms = []
        for csig in conv_sigs:
            unblind_msg = self.group.unblind(csig, bkey)
            nyms.append(unblind_msg["nym"])
        self.assertNotEqual(nyms[0], nyms[1])

    def test_3e_blindNonTransitiveConvertUnblind(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig2_msg = self.group.sign(text, memkey)
        blind_msg = self.group.blind(text, sig_msg["signature"])
        bkey = key(b64=blind_msg["blind_key"])
        blind2_msg = self.group.blind(
            text, sig2_msg["signature"], blind_key=bkey
        )
        conv_msg = self.group.convert(
            [blind_msg["blind_signature"]], bkey.public()
        )
        conv2_msg = self.group.convert(
            [blind2_msg["blind_signature"]], bkey.public()
        )
        unblind_msg = self.group.unblind(
            conv_msg["converted_signatures"][0], bkey
        )
        unblind2_msg = self.group.unblind(
            conv2_msg["converted_signatures"][0], bkey
        )
        self.assertNotEqual(unblind_msg["nym"], unblind2_msg["nym"])


class TestBaseExportImport(SetUpMixin, AddMemberMixin):
    def test_4a_exportImportGroupKey(self):
        gkey_b64 = self.group.grpkey.to_b64()
        gkey = key(self.scheme, "group")
        gkey.set_b64(gkey_b64)
        self.assertEqual(str(gkey), str(self.group.grpkey))
        gkey2 = key(b64=gkey_b64)
        self.assertEqual(str(gkey2), str(self.group.grpkey))

    def test_4b_exportImportManagerKey(self):
        mgkey_b64 = self.group.mgrkey.to_b64()
        mgkey = key(self.scheme, "manager")
        mgkey.set_b64(mgkey_b64)
        self.assertEqual(str(mgkey), str(self.group.mgrkey))
        mgkey2 = key(b64=mgkey_b64)
        self.assertEqual(str(mgkey2), str(self.group.mgrkey))

    def test_4c_exportImportMemberKey(self):
        _mkey = self.addMember()
        mkey_b64 = _mkey.to_b64()
        mkey = key(self.scheme, "member")
        mkey.set_b64(mkey_b64)
        self.assertEqual(str(mkey), str(_mkey))
        mkey2 = key(b64=mkey_b64)
        self.assertEqual(str(mkey2), str(_mkey))

    def test_4d_exportImportSignature(self):
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        sig = signature(self.scheme)
        sig.set_b64(sig_msg["signature"])
        ver_msg = self.group.verify(text, sig.to_b64())
        self.assertEqual(ver_msg["status"], "success")
        sig2 = signature(b64=sig_msg["signature"])
        ver_msg2 = self.group.verify(text, sig2.to_b64())
        self.assertEqual(ver_msg2["status"], "success")

    def test_4e_exportImportGML(self):
        if hasattr(self.group, "gml"):
            self.addMember()
            self.addMember()
            gml_b64 = self.group.gml.to_b64()
            gml = GML()
            gml.set_b64(gml_b64)
            self.assertEqual(str(gml), str(self.group.gml))
            gml2 = GML.from_b64(gml_b64)
            self.assertEqual(str(gml2), str(self.group.gml))
        else:
            raise unittest.SkipTest("Requires GML")


class TestBlindExportImport:
    def test_4f_exportImportBlindKey(self):
        from pygroupsig.schemes.gl19 import BlindKey

        bkey = BlindKey.from_random(self.group.grpkey)
        bkey_b64 = bkey.to_b64()
        bkey2 = key(self.scheme, "blind")
        bkey2.set_b64(bkey_b64)
        self.assertEqual(str(bkey2), str(bkey))
        bkey3 = key(b64=bkey_b64)
        self.assertEqual(str(bkey3), str(bkey))
