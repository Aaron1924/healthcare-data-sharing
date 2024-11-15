import logging

from pygroupsig import group, key, load_library, signature
from pygroupsig.helpers import GML


class SetUpMixin:
    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)
        self.group.setup()
        self.memkeys = []


class AddMemberMixin:
    def addMember(self):
        memkey = key(self.scheme, "member")
        msg1 = self.group.join_mgr()
        msg2 = self.group.join_mem(msg1, memkey)
        msg3 = self.group.join_mgr(msg2)
        _ = self.group.join_mem(msg3, memkey)
        self.memkeys.append(memkey)
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
        self.memkeys.append(memkey)
        return memkey

    def addMemberIsolated(self):
        gs = group(self.scheme)
        gs.setup()
        memkey = key(self.scheme, "member")
        msg1 = gs.join_mgr()
        _ = gs.join_mem(msg1, memkey)
        return gs, memkey

    def test_addMember(self):
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


class TestBaseOps(AddMemberMixin):
    def setUp(self):
        load_library()
        if self.scheme is None:
            raise ValueError("Missing scheme")
        self.group = group(self.scheme)
        self.memkeys = []

    def test_group(self):
        for v in vars(self.group.grpkey):
            self.assertTrue(getattr(self.group.grpkey, v).is_zero())
        for v in vars(self.group.mgrkey):
            self.assertTrue(getattr(self.group.mgrkey, v).is_zero())
        if hasattr(self.group, "gml"):
            self.assertFalse(self.group.gml)

    def test_setup(self):
        self.group.setup()
        for v in vars(self.group.grpkey):
            self.assertFalse(getattr(self.group.grpkey, v).is_zero())
        for v in vars(self.group.mgrkey):
            self.assertFalse(getattr(self.group.mgrkey, v).is_zero())

    def test_memKey(self):
        memkey = key(self.scheme, "member")
        for v in vars(memkey):
            el = getattr(memkey, v)
            if isinstance(el, int):
                self.assertEqual(el, -1)
            else:
                self.assertTrue(getattr(memkey, v).is_zero())

    def test_addMember(self):
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

    def test_validSignature(self):
        self.group.setup()
        memkey = self.addMember()
        text = "Hello world!"
        sig_msg = self.group.sign(text, memkey)
        self.assertEqual(sig_msg["status"], "success")
        ver_msg = self.group.verify(text, sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "success")

    def test_invalidSignatureMessage(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        self.assertEqual(sig_msg["status"], "success")
        ver_msg = self.group.verify("World hello!", sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "fail")

    def test_invalidSignature(self):
        gs, memkey = self.addMemberIsolated()
        self.group.setup()
        logging.getLogger(f"pygroupsig.schemes.{self.scheme}").setLevel(
            logging.CRITICAL
        )
        text = "Hello world!"
        sig_msg = gs.sign(text, memkey)
        self.assertEqual(sig_msg["status"], "success")
        ver_msg = self.group.verify(text, sig_msg["signature"])
        self.assertEqual(ver_msg["status"], "fail")


class TestOpenVerifyMixin:
    def test_openSignatureValidProof(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        self.assertEqual(open_msg["status"], "success")
        openver_msg = self.group.open_verify(
            sig_msg["signature"], open_msg["proof"]
        )
        self.assertEqual(openver_msg["status"], "success")

    def test_openSignatureInvalidProof(self):
        self.group.setup()
        gs, memkey = self.addMemberIsolated()
        sig_msg = gs.sign("Hello world!", memkey)
        open_msg = gs.open(sig_msg["signature"])
        self.assertEqual(open_msg["status"], "success")
        openver_msg = self.group.open_verify(
            sig_msg["signature"], open_msg["proof"]
        )
        self.assertEqual(openver_msg["status"], "fail")


class TestOpenMixin:
    def test_openSignature(self):
        self.group.setup()
        memkey = self.addMember()
        sig_msg = self.group.sign("Hello world!", memkey)
        open_msg = self.group.open(sig_msg["signature"])
        self.assertEqual(open_msg["status"], "success")
        self.assertNotEqual(open_msg["id"], "")


class TestBaseKeyOps(SetUpMixin, AddMemberMixin):
    def test_exportImportGroupKey(self):
        gkey_b64 = self.group.grpkey.to_b64()
        gkey = key(self.scheme, "group")
        gkey.set_b64(gkey_b64)
        self.assertEqual(str(gkey), str(self.group.grpkey))
        gkey2 = key(b64=gkey_b64)
        self.assertEqual(str(gkey2), str(self.group.grpkey))

    def test_exportImportManagerKey(self):
        mgkey_b64 = self.group.mgrkey.to_b64()
        mgkey = key(self.scheme, "manager")
        mgkey.set_b64(mgkey_b64)
        self.assertEqual(str(mgkey), str(self.group.mgrkey))
        mgkey2 = key(b64=mgkey_b64)
        self.assertEqual(str(mgkey2), str(self.group.mgrkey))

    def test_exportImportMemberKey(self):
        _mkey = self.addMember()
        mkey_b64 = _mkey.to_b64()
        mkey = key(self.scheme, "member")
        mkey.set_b64(mkey_b64)
        self.assertEqual(str(mkey), str(_mkey))
        mkey2 = key(b64=mkey_b64)
        self.assertEqual(str(mkey2), str(_mkey))


class TestBaseSignatureOps(SetUpMixin, AddMemberMixin):
    def test_exportImport(self):
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


class TestBaseGMLOps(SetUpMixin, AddMemberMixin):
    def test_gml(self):
        self.addMember()
        self.addMember()
        self.addMember()
        self.addMember()
        self.addMember()
        self.assertEqual(len(self.group.gml), len(self.memkeys))

    def test_exportImport(self):
        self.addMember()
        self.addMember()
        gml_b64 = self.group.gml.to_b64()
        gml = GML()
        gml.set_b64(gml_b64)
        self.assertEqual(str(gml), str(self.group.gml))
        gml2 = GML.from_b64(gml_b64)
        self.assertEqual(str(gml2), str(self.group.gml))
