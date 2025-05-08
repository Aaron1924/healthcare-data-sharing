import unittest

from tests.helpers import (
    TestBase,
    TestBaseExportImport,
    TestBlind,
    TestBlindExportImport,
    TestLink,
    TestLinkSeq,
    TestOpen,
    TestOpenVerify,
    TestReveal,
)


class Test_1a_BBS04GroupOps(TestOpen, TestBase, unittest.TestCase):
    scheme = "bbs04"


class Test_1b_BBS04ExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "bbs04"


class Test_2a_PS16GroupOps(
    TestOpenVerify, TestOpen, TestBase, unittest.TestCase
):
    scheme = "ps16"


class Test_2b_PS16ExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "ps16"


class Test_3a_CPY06GroupOps(TestOpen, TestBase, unittest.TestCase):
    scheme = "cpy06"


class Test_3b_CPY06RevealOps(TestReveal, unittest.TestCase):
    scheme = "cpy06"


class Test_3c_CPY06ExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "cpy06"


class Test_4a_KLAP20GroupOps(
    TestOpenVerify, TestOpen, TestBase, unittest.TestCase
):
    scheme = "klap20"


class Test_4b_KLAP20ExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "klap20"


class Test_5a_GL19GroupOps(TestBase, unittest.TestCase):
    scheme = "gl19"


class Test_5b_GL19BlindOps(TestBlind, unittest.TestCase):
    scheme = "gl19"


class Test_5c_GL19ExportImportOps(
    TestBlindExportImport, TestBaseExportImport, unittest.TestCase
):
    scheme = "gl19"


class Test_6a_DL21GroupOps(TestBase, unittest.TestCase):
    scheme = "dl21"


class Test_6b_DL21LinkOps(TestLink, unittest.TestCase):
    scheme = "dl21"


class Test_6c_DL21ExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "dl21"


class Test_7a_DL21SEQGroupOps(TestBase, unittest.TestCase):
    scheme = "dl21seq"


class Test_7b_DL21SEQLinkOps(TestLinkSeq, TestLink, unittest.TestCase):
    scheme = "dl21seq"


class Test_7c_DL21SEQExportImportOps(TestBaseExportImport, unittest.TestCase):
    scheme = "dl21seq"


if __name__ == "__main__":
    unittest.main()
