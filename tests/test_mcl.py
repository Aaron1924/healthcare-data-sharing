from pygroupsig import load_library
from pygroupsig.pairings.mcl import Fp, Fp2, Fr, G1, G2, GT
import pygroupsig.pairings.utils as ut
from pathlib import Path
import unittest


class FBaseTest(unittest.TestCase):
    def setUp(self):
        load_library()

    def _testByteSize(self, cls, value):
        self.assertEqual(cls.byte_size(), value)

    def _testStr(self, cls):
        x = cls()
        s = "1234567890987654321"
        x.set_str(s)
        self.assertEqual(x.get_str(), s)

    def _testInt(self, cls):
        x = cls()
        i = 1234567890987654321
        x.set_int(i)
        y = cls()
        y.set_str(str(i))
        self.assertEqual(x.get_str(), y.get_str())

    def _testIsZero(self, cls):
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(0)
        else:
            x.set_int(0)
        self.assertIs(x.is_zero(), True)
        if fp2:
            x.d[0].set_int(1)
        else:
            x.set_int(1)
        self.assertIs(x.is_zero(), False)

    def _testIsOne(self, cls):
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(1)
        else:
            x.set_int(1)
        self.assertIs(x.is_one(), True)
        if fp2:
            x.d[0].set_int(0)
        else:
            x.set_int(0)
        self.assertIs(x.is_one(), False)

    def _testIsEqual(self, cls):
        x = cls()
        y = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(42)
        else:
            x.set_int(42)
            y.set_int(42)
        self.assertIs(x.is_equal(y), True)
        self.assertIs(x == y, True)
        self.assertIs(y.is_equal(x), True)
        self.assertIs(y == x, True)
        if fp2:
            y.d[0].set_int(41)
        else:
            y.set_int(41)
        self.assertIs(x.is_equal(y), False)
        self.assertIs(x == y, False)
        self.assertIs(y.is_equal(x), False)
        self.assertIs(y == x, False)

    def _testCmp(self, cls):
        x = cls()
        x.set_int(42)
        y = cls()
        y.set_int(41)
        self.assertEqual(x.cmp(y), 1)
        self.assertIs(x > y, True)
        self.assertIs(x >= y, True)
        self.assertEqual(y.cmp(x), -1)
        self.assertIs(y < x, True)
        self.assertIs(y <= x, True)
        y.set_int(42)
        self.assertEqual(x.cmp(y), 0)
        self.assertIs(x > y, False)
        self.assertIs(x >= y, True)
        self.assertEqual(y.cmp(x), 0)
        self.assertIs(y < x, False)
        self.assertIs(y <= x, True)

    def _testNeg(self, cls):
        x = cls()
        y = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(-42)
        else:
            x.set_int(42)
            y.set_int(-42)
        x_n = -x
        self.assertIs(x == x_n, False)
        x_p = -x_n
        self.assertIs(x == x_p, True)
        self.assertIs(x_n == y, True)
        y_n = -y
        self.assertIs(y_n == x, True)

    def _testMul(self, cls):
        x = cls()
        y = cls()
        z = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(6)
            y.d[0].set_int(7)
            z.d[0].set_int(42)
        else:
            x.set_int(6)
            y.set_int(7)
            z.set_int(42)
        z_p = x.mul(y)
        z_p2 = x * y
        z2_p = y.mul(x)
        z2_p2 = y * x
        self.assertIs(z_p == z_p2 == z, True)
        self.assertIs(z2_p == z2_p2 == z, True)

    def _testDiv(self, cls):
        x = cls()
        y = cls()
        z = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(7)
            z.d[0].set_int(6)
        else:
            x.set_int(42)
            y.set_int(7)
            z.set_int(6)
        z_p = x.div(y)
        z_p2 = x / y
        self.assertIs(z_p == z_p2 == z, True)

    def _testAdd(self, cls):
        x = cls()
        y = cls()
        z = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(6)
            y.d[0].set_int(36)
            z.d[0].set_int(42)
        else:
            x.set_int(6)
            y.set_int(36)
            z.set_int(42)
        z_p = x.add(y)
        z_p2 = x + y
        z2_p = y.add(x)
        z2_p2 = y + x
        self.assertIs(z_p == z_p2 == z, True)
        self.assertIs(z2_p == z2_p2 == z, True)

    def _testSub(self, cls):
        x = cls()
        y = cls()
        z = cls()
        z2 = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(6)
            z.d[0].set_int(36)
            z2.d[0].set_int(-36)
        else:
            x.set_int(42)
            y.set_int(6)
            z.set_int(36)
            z2.set_int(-36)
        z_p = x.sub(y)
        z_p2 = x - y
        z2_p = y.sub(x)
        z2_p2 = y - x
        self.assertIs(z_p == z_p2 == z, True)
        self.assertIs(z2_p == z2_p2 == z2, True)

    def _testInv(self, cls):
        one = cls()
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            one.d[0].set_int(1)
            x.d[0].set_int(42)
        else:
            one.set_int(1)
            x.set_int(42)
        x_i = x.inv()
        x_i2 = ~x
        pd = x * x_i
        pd2 = x * x_i2
        x_p = ~x_i
        self.assertIs(pd == pd2 == one, True)
        self.assertIs(x == x_p, True)

    def _testPow(self, cls):
        x = cls()
        x.set_int(2)
        y = cls()
        y.set_int(5)
        z = cls()
        z.set_int(32)
        z_p = x.pow(y)
        z_p2 = x ** y
        self.assertIs(z_p == z_p2 == z, True)

    def _testSetRandom(self, cls):
        x = cls()
        x.set_int(10)
        self.assertEqual(x.get_str(), "10")
        x.set_random()
        self.assertNotEqual(x.get_str(), "10")


    def _testSerialization(self, cls):
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        x_b = x.to_bytes()
        y = cls()
        y.set_from_bytes(x_b)
        y_p = cls.from_bytes(x_b)
        self.assertIs(x == y == y_p, True)

    def _testSetHash(self, cls):
        x = cls()
        x.set_int(42)
        y = cls()
        y.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, False)
        x.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, True)

    def _testFile(self, cls):
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        f = Path("/tmp/.test_pairings.txt")
        x.to_file(f)
        y = cls()
        y.set_from_file(f)
        y_p = cls.from_file(f)
        self.assertIs(x == y == y_p, True)

    def _testB64(self, cls):
        x = cls()
        fp2 = isinstance(x, Fp2)
        if fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        x_b64 = x.to_b64()
        y = cls()
        y.set_from_b64(x_b64)
        y_p = cls.from_b64(x_b64)
        self.assertIs(x == y == y_p, True)


class TestFp(FBaseTest):
    def testByteSize(self):
        self._testByteSize(Fp, 48)

    def testStr(self):
        self._testStr(Fp)

    def testInt(self):
        self._testInt(Fp)

    def testIsZero(self):
        self._testIsZero(Fp)

    def testIsOne(self):
        self._testIsOne(Fp)

    def testIsEqual(self):
        self._testIsEqual(Fp)

    def testCmp(self):
        self._testCmp(Fp)

    def testNeg(self):
        self._testNeg(Fp)

    def testMul(self):
        self._testMul(Fp)

    def testDiv(self):
        self._testDiv(Fp)

    def testAdd(self):
        self._testAdd(Fp)

    def testSub(self):
        self._testSub(Fp)

    def testInv(self):
        self._testInv(Fp)

    def testPow(self):
        self._testPow(Fp)

    def testSetRandom(self):
        self._testSetRandom(Fp)

    def testSerialization(self):
        self._testSerialization(Fp)

    def testSetHash(self):
        self._testSetHash(Fp)

    def testFile(self):
        self._testFile(Fp)

    def testB64(self):
        self._testB64(Fp)


class TestFr(FBaseTest):
    def testByteSize(self):
        self._testByteSize(Fr, 32)

    def testStr(self):
        self._testStr(Fr)

    def testInt(self):
        self._testInt(Fr)

    def testIsZero(self):
        self._testIsZero(Fr)

    def testIsOne(self):
        self._testIsOne(Fr)

    def testIsEqual(self):
        self._testIsEqual(Fr)

    def testCmp(self):
        self._testCmp(Fr)

    def testNeg(self):
        self._testNeg(Fr)

    def testMul(self):
        self._testMul(Fr)

    def testDiv(self):
        self._testDiv(Fr)

    def testAdd(self):
        self._testAdd(Fr)

    def testSub(self):
        self._testSub(Fr)

    def testInv(self):
        self._testInv(Fr)

    def testPow(self):
        self._testPow(Fr)

    def testSetRandom(self):
        self._testSetRandom(Fr)

    def testSerialization(self):
        self._testSerialization(Fr)

    def testSetHash(self):
        self._testSetHash(Fr)

    def testFile(self):
        self._testFile(Fr)

    def testB64(self):
        self._testB64(Fr)


class TestFp2(FBaseTest):
    def testByteSize(self):
        self._testByteSize(Fp2, 96)

    def testIsZero(self):
        self._testIsZero(Fp2)

    def testIsOne(self):
        self._testIsOne(Fp2)

    def testIsEqual(self):
        self._testIsEqual(Fp2)

    def testNeg(self):
        self._testNeg(Fp2)

    def testMul(self):
        self._testMul(Fp2)

    def testDiv(self):
        self._testDiv(Fp2)

    def testAdd(self):
        self._testAdd(Fp2)

    def testSub(self):
        self._testSub(Fp2)

    def testInv(self):
        self._testInv(Fp2)

    def testSerialization(self):
        self._testSerialization(Fp2)

    def testFile(self):
        self._testFile(Fp2)

    def testB64(self):
        self._testB64(Fp2)


class GBaseTest(unittest.TestCase):
    def setUp(self):
        load_library()
        if isinstance(self, TestG1):
            self.s = ut.BLS12_381_P
        else:
            self.s = ut.BLS12_381_Q

    def _testByteSize(self, cls, value):
        self.assertEqual(cls.byte_size(), value)

    def _testStr(self, cls):
        x = cls()
        x.set_str(self.s)
        self.assertEqual(x.get_str(), self.s)

    def _testIsZero(self, cls):
        x = cls()
        x.set_str(self.s)
        self.assertIs(x.is_zero(), False)
        x.set_str("0")
        self.assertIs(x.is_zero(), True)

    def _testIsEqual(self, cls):
        x = cls()
        x.set_str(self.s)
        y = cls()
        y.set_str(self.s)
        self.assertIs(x.is_equal(y), True)
        self.assertIs(x == y, True)
        self.assertIs(y.is_equal(x), True)
        self.assertIs(y == x, True)
        y.set_str("0")
        self.assertIs(x.is_equal(y), False)
        self.assertIs(x == y, False)
        self.assertIs(y.is_equal(x), False)
        self.assertIs(y == x, False)

    def _testNeg(self, cls):
        x = cls()
        x.set_str(self.s)
        x_n = -x
        self.assertIs(x == x_n, False)
        x_p = -x_n
        self.assertIs(x == x_p, True)

    def _testMul(self, cls):
        x = cls()
        x.set_str(self.s)
        y = Fr()
        y.set_int(0)
        z_p = x.mul(y)
        z_p2 = x * y
        self.assertIs(z_p == z_p2, True)
        self.assertEqual(z_p2.get_str(), "0")

    def _testMulVec(self, cls):
        n = 42
        x = (cls * n)()
        y = (Fr * n)()
        for i in range(n):
            x[i].set_str(self.s)
            if i % 2:
                y[i].set_int(-1)
            else:
                y[i].set_int(1)
        z = cls()
        z.muln(x, y)
        self.assertEqual(z.get_str(), "0")

    def _testAdd(self, cls):
        x = cls()
        x.set_str(self.s)
        y = Fr()
        y.set_int(2)
        z = x.add(x)
        z2 = x + x
        z_p = x * y
        self.assertIs(z == z2, True)
        self.assertIs(z == z_p, True)

    def _testSub(self, cls):
        x = cls()
        x.set_str(self.s)
        z = x.sub(x)
        z2 = x - x
        self.assertIs(z == z2, True)
        self.assertIs(z.is_zero(), True)

    def _testSerialization(self, cls):
        x = cls()
        x.set_str(self.s)
        x_b = x.to_bytes()
        y = cls()
        y.set_from_bytes(x_b)
        y_p = cls.from_bytes(x_b)
        self.assertIs(x == y == y_p, True)

    def _testSetHash(self, cls):
        x = cls()
        x.set_str(self.s)
        y = cls()
        y.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, False)
        x.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, True)

    def _testFile(self, cls):
        x = cls()
        x.set_str(self.s)
        f = Path("/tmp/.test_pairings.txt")
        x.to_file(f)
        y = cls()
        y.set_from_file(f)
        y_p = y.from_file(f)
        self.assertIs(x == y == y_p, True)

    def _testB64(self, cls):
        x = cls()
        x.set_str(self.s)
        x_b64 = x.to_b64()
        y = cls()
        y.set_from_b64(x_b64)
        y_p = y.from_b64(x_b64)
        self.assertIs(x == y == y_p, True)

    def _testSetRandom(self, cls):
        x = cls()
        x.set_random()
        self.assertIs(x.is_zero(), False)
        y = cls()
        y.set_random()
        self.assertIs(y.is_zero(), False)
        self.assertIs(x == y, False)
        self.assertNotEqual(x.get_str(), y.get_str())


class TestG1(GBaseTest):
    def testByteSize(self):
        self._testByteSize(G1, 48)

    def testStr(self):
        self._testStr(G1)

    def testIsZero(self):
        self._testIsZero(G1)

    def testIsEqual(self):
        self._testIsEqual(G1)

    def testNeg(self):
        self._testNeg(G1)

    def testMul(self):
        self._testMul(G1)

    def testMulVec(self):
        self._testMulVec(G1)

    def testAdd(self):
        self._testAdd(G1)

    def testSub(self):
        self._testSub(G1)

    def testSerialization(self):
        self._testSerialization(G1)

    def testSetHash(self):
        self._testSetHash(G1)

    def testFile(self):
        self._testFile(G1)

    def testB64(self):
        self._testB64(G1)

    def testSetRandom(self):
        self._testSetRandom(G1)


class TestG2(GBaseTest):
    def testByteSize(self):
        self._testByteSize(G2, 96)

    def testStr(self):
        self._testStr(G2)

    def testIsZero(self):
        self._testIsZero(G2)

    def testIsEqual(self):
        self._testIsEqual(G2)

    def testNeg(self):
        self._testNeg(G2)

    def testMul(self):
        self._testMul(G2)

    def testMulVec(self):
        self._testMulVec(G2)

    def testAdd(self):
        self._testAdd(G2)

    def testSub(self):
        self._testSub(G2)

    def testSerialization(self):
        self._testSerialization(G2)

    def testSetHash(self):
        self._testSetHash(G2)

    def testFile(self):
        self._testFile(G2)

    def testB64(self):
        self._testB64(G2)

    def testSetRandom(self):
        self._testSetRandom(G2)


class TestGT(FBaseTest):
    def testByteSize(self):
        self._testByteSize(GT, 576)

    def testStr(self):
        x = GT()
        s = "1 2 3 4 5 6 7 8 9 10 11 12"
        x.set_str(s)
        self.assertEqual(x.get_str(), s)

    def testInt(self):
        x = GT()
        x.set_int(42)
        self.assertEqual(x.get_str(), "42 0 0 0 0 0 0 0 0 0 0 0")

    def testIsZero(self):
        self._testIsZero(GT)

    def testIsOne(self):
        self._testIsOne(GT)

    def testIsEqual(self):
        self._testIsEqual(GT)

    def testNeg(self):
        self._testNeg(GT)

    def testMul(self):
        self._testMul(GT)

    def testDiv(self):
        self._testDiv(GT)

    def testAdd(self):
        self._testAdd(GT)

    def testSub(self):
        self._testSub(GT)

    def testInv(self):
        # TODO
        # self._testInv(GT)
        pass

    def testPow(self):
        # TODO
        # self._testPow(GT)
        pass

    def testSerialization(self):
        self._testSerialization(GT)

    def testFile(self):
        self._testFile(GT)

    def testB64(self):
        self._testB64(GT)

    def testPowVec(self):
        # TODO
        # self._testPowVec(GT)
        pass

    def testPairing(self):
        # TODO
        # self._testPairing(GT)
        pass


if __name__ == '__main__':
    unittest.main()
