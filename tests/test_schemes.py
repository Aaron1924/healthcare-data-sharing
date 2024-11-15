import unittest

from tests.mixins import (
    AddMember2Mixin,
    TestBaseGMLOps,
    TestBaseKeyOps,
    TestBaseOps,
    TestBaseSignatureOps,
    TestOpenMixin,
    TestOpenVerifyMixin,
)


class TestBBS04GroupOps(
    TestOpenMixin, AddMember2Mixin, TestBaseOps, unittest.TestCase
):
    scheme = "bbs04"


class TestBBS04KeyOps(AddMember2Mixin, TestBaseKeyOps, unittest.TestCase):
    scheme = "bbs04"


class TestBBS04SignatureOps(
    AddMember2Mixin, TestBaseSignatureOps, unittest.TestCase
):
    scheme = "bbs04"


class TestBBS04GMLOps(AddMember2Mixin, TestBaseGMLOps, unittest.TestCase):
    scheme = "bbs04"


class TestPS16GroupOps(TestOpenVerifyMixin, TestBaseOps, unittest.TestCase):
    scheme = "ps16"


class TestPS16KeyOps(TestBaseKeyOps, unittest.TestCase):
    scheme = "ps16"


class TestPS16SignatureOps(TestBaseSignatureOps, unittest.TestCase):
    scheme = "ps16"


class TestPS16GMLOps(TestBaseGMLOps, unittest.TestCase):
    scheme = "ps16"


class TestCPY06GroupOps(TestOpenMixin, TestBaseOps, unittest.TestCase):
    scheme = "cpy06"


class TestCPY06KeyOps(TestBaseKeyOps, unittest.TestCase):
    scheme = "cpy06"


class TestCPY06SignatureOps(TestBaseSignatureOps, unittest.TestCase):
    scheme = "cpy06"


class TestCPY06GMLOps(TestBaseGMLOps, unittest.TestCase):
    scheme = "cpy06"


class TestKLAP20GroupOps(TestOpenVerifyMixin, TestBaseOps, unittest.TestCase):
    scheme = "klap20"


class TestKLAP20KeyOps(TestBaseKeyOps, unittest.TestCase):
    scheme = "klap20"


class TestKLAP20SignatureOps(TestBaseSignatureOps, unittest.TestCase):
    scheme = "klap20"


class TestKLAP20GMLOps(TestBaseGMLOps, unittest.TestCase):
    scheme = "klap20"


class TestGL19GroupOps(TestBaseOps, unittest.TestCase):
    scheme = "gl19"


class TestGL19KeyOps(TestBaseKeyOps, unittest.TestCase):
    scheme = "gl19"


class TestGL19SignatureOps(TestBaseSignatureOps, unittest.TestCase):
    scheme = "gl19"


class TestDL21GroupOps(TestBaseOps, unittest.TestCase):
    scheme = "dl21"


class TestDL21KeyOps(TestBaseKeyOps, unittest.TestCase):
    scheme = "dl21"


class TestDL21SignatureOps(TestBaseSignatureOps, unittest.TestCase):
    scheme = "dl21"


if __name__ == "__main__":
    unittest.main()
