import unittest
from pathlib import Path

import pygroupsig.utils.constants as ct
from pygroupsig.utils.mcl import G1, G2, GT, Fp, Fp2, Fr


class FBaseTest(unittest.TestCase):
    def _testByteSize(self, cls, value):
        self.assertEqual(cls.byte_size(), value)

    def _testStr(self, cls):
        s = "1234567890987654321"
        x = cls()
        x.set_str(s)
        y = cls.from_str(s)
        self.assertEqual(x.get_str(), s)
        self.assertEqual(x.get_str(), y.get_str())

    def _testBytes(self, cls):
        x = cls.from_str("1234567890987654321")
        x_b = x.to_bytes()
        y = cls()
        y.set_bytes(x_b)
        z = cls.from_bytes(x_b)
        self.assertEqual(x.get_str(), y.get_str())
        self.assertEqual(x.get_str(), z.get_str())

    def _testInt(self, cls):
        i = 1234567890987654321
        x = cls()
        x.set_int(i)
        y = cls.from_int(i)
        z = cls.from_str(str(i))
        self.assertEqual(x.get_str(), y.get_str())
        self.assertEqual(x.get_str(), z.get_str())

    def _testIsZero(self, cls):
        fp2 = cls == Fp2
        x = cls()
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
        fp2 = cls == Fp2
        x = cls()
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
        fp2 = cls == Fp2
        x = cls()
        y = cls()
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
        x = cls.from_int(42)
        y = cls.from_int(41)
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
        if cls == Fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(-42)
        else:
            x.set_int(42)
            y.set_int(-42)
        x_n = -x
        self.assertIs(x == x_n, False)
        xx = -x_n
        self.assertIs(x == xx, True)
        self.assertIs(x_n == y, True)
        y_n = -y
        self.assertIs(y_n == x, True)

    def _testMul(self, cls):
        x = cls()
        y = cls()
        z = cls()
        if cls == Fp2:
            x.d[0].set_int(6)
            y.d[0].set_int(7)
            z.d[0].set_int(42)
        else:
            x.set_int(6)
            y.set_int(7)
            z.set_int(42)
        a = x.mul(y)
        aa = x * y
        self.assertIs(a == aa == z, True)
        b = y.mul(x)
        bb = y * x
        self.assertIs(b == bb == z, True)

    def _testDiv(self, cls):
        x = cls()
        y = cls()
        z = cls()
        if cls == Fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(7)
            z.d[0].set_int(6)
        else:
            x.set_int(42)
            y.set_int(7)
            z.set_int(6)
        a = x.div(y)
        aa = x / y
        self.assertIs(a == aa == z, True)

    def _testAdd(self, cls):
        x = cls()
        y = cls()
        z = cls()
        if cls == Fp2:
            x.d[0].set_int(6)
            y.d[0].set_int(36)
            z.d[0].set_int(42)
        else:
            x.set_int(6)
            y.set_int(36)
            z.set_int(42)
        a = x.add(y)
        aa = x + y
        self.assertIs(a == aa == z, True)
        b = y.add(x)
        bb = y + x
        self.assertIs(b == bb == z, True)

    def _testSub(self, cls):
        x = cls()
        y = cls()
        z = cls()
        z_n = cls()
        if cls == Fp2:
            x.d[0].set_int(42)
            y.d[0].set_int(6)
            z.d[0].set_int(36)
            z_n.d[0].set_int(-36)
        else:
            x.set_int(42)
            y.set_int(6)
            z.set_int(36)
            z_n.set_int(-36)
        a = x.sub(y)
        aa = x - y
        self.assertIs(a == aa == z, True)
        b = y.sub(x)
        bb = y - x
        self.assertIs(b == bb == z_n, True)

    def _testInv(self, cls):
        one = cls()
        x = cls()
        if cls == Fp2:
            one.d[0].set_int(1)
            x.d[0].set_int(42)
        else:
            one.set_int(1)
            x.set_int(42)
        x_i = x.inv()
        x_ii = ~x
        self.assertIs(x_i == x_ii, True)
        p = x * x_i
        self.assertIs(p == one, True)
        x_p = ~x_i
        self.assertIs(x == x_p, True)

    def _testPow(self, cls):
        x = cls.from_int(2)
        y = cls.from_int(5)
        z = cls.from_int(32)
        a = x.pow(y)
        aa = x**y
        self.assertIs(a == aa == z, True)

    def _testSetRandom(self, cls):
        x = cls.from_int(10)
        self.assertEqual(x.get_str(), "10")
        x.set_random()
        self.assertNotEqual(x.get_str(), "10")
        y = cls.from_random()
        self.assertEqual(y.is_zero(), False)

    def _testSerialization(self, cls):
        x = cls()
        if cls == Fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        x_b = x.to_bytes()
        y = cls()
        y.set_bytes(x_b)
        z = cls.from_bytes(x_b)
        self.assertIs(x == y == z, True)

    def _testSetHash(self, cls):
        x = cls.from_int(42)
        y = cls()
        y.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, False)
        z = cls.from_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(y == z, True)
        x.set_hash("a1d0c6e83f027327d8461063f4ac58a6")
        self.assertIs(x == y, True)

    def _testFile(self, cls):
        x = cls()
        if cls == Fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        f = Path("/tmp/.test_mcl.txt")
        x.to_file(f)
        y = cls()
        y.set_file(f)
        z = cls.from_file(f)
        self.assertIs(x == y == z, True)

    def _testB64(self, cls):
        x = cls()
        if cls == Fp2:
            x.d[0].set_int(42)
        else:
            x.set_int(42)
        x_b64 = x.to_b64()
        y = cls()
        y.set_b64(x_b64)
        z = cls.from_b64(x_b64)
        self.assertIs(x == y == z, True)


class TestFp(FBaseTest):
    def testByteSize(self):
        self._testByteSize(Fp, 48)

    def testStr(self):
        self._testStr(Fp)

    def testBytes(self):
        self._testBytes(Fp)

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

    def testBytes(self):
        self._testBytes(Fr)

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
        self.h = (
            "f0c8dc42d5a51db0c326916d10392adbf76b14ae99d489ff3560611a97420eee"
        )
        self.s = ct.BLS12_381_P
        self.v = "1 3719226684904596419579221578361625155541235735183967430228173297117758812288229752053408139708879506501457152802942 260918097660325786349299603372812253806953498958308283336009514870956832500285249250447899736364680533026929093718"
        if isinstance(self, TestG2):
            self.s = ct.BLS12_381_Q
            self.v = "1 835291197291119138835982130627849483202366689768919374128556270083673076425684408356112030969361574591025123607949 262446842239551949853427194215207084960530636993308253549525386344727618348891416626249682329755634097133131050377 1485374626780584277638246857402993053167420159545306011973894843376495696555900277040606767721288523043305649236038 3253563504197550909989288629072739120866164573027127387470195401209461645203269415741294914321252541506907241635197"

    def _testByteSize(self, cls, value):
        self.assertEqual(cls.byte_size(), value)

    def _testStr(self, cls):
        x = cls.from_generator()
        self.assertEqual(x.get_str(), self.s)

    def _testBytes(self, cls):
        x = cls.from_generator()
        x_b = x.to_bytes()
        y = cls()
        y.set_bytes(x_b)
        z = cls.from_bytes(x_b)
        self.assertEqual(x.get_str(), y.get_str())
        self.assertEqual(x.get_str(), z.get_str())

    def _testIsZero(self, cls):
        x = cls.from_generator()
        self.assertIs(x.is_zero(), False)
        x.set_str("0")
        self.assertIs(x.is_zero(), True)

    def _testIsEqual(self, cls):
        x = cls.from_generator()
        y = cls.from_generator()
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
        x = cls.from_generator()
        x_n = -x
        self.assertIs(x == x_n, False)
        x_p = -x_n
        self.assertIs(x == x_p, True)

    def _testMul(self, cls):
        x = cls.from_generator()
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
            x[i].set_generator()
            if i % 2:
                y[i].set_int(-1)
            else:
                y[i].set_int(1)
        z = cls()
        z.muln(x, y)
        self.assertEqual(z.get_str(), "0")

    def _testAdd(self, cls):
        x = cls.from_generator()
        y = Fr()
        y.set_int(2)
        z = x.add(x)
        z2 = x + x
        z_p = x * y
        self.assertIs(z == z2, True)
        self.assertIs(z == z_p, True)

    def _testSub(self, cls):
        x = cls.from_generator()
        z = x.sub(x)
        z2 = x - x
        self.assertIs(z == z2, True)
        self.assertIs(z.is_zero(), True)

    def _testSerialization(self, cls):
        x = cls.from_generator()
        x_b = x.to_bytes()
        y = cls()
        y.set_bytes(x_b)
        y_p = cls.from_bytes(x_b)
        self.assertIs(x == y == y_p, True)

    def _testSetHash(self, cls):
        x = cls()
        x.set_hash(self.h)
        self.assertEqual(x.get_str(), self.v)

    def _testFile(self, cls):
        x = cls.from_generator()
        f = Path("/tmp/.test_mcl.txt")
        x.to_file(f)
        y = cls()
        y.set_file(f)
        y_p = y.from_file(f)
        self.assertIs(x == y == y_p, True)

    def _testB64(self, cls):
        x = cls.from_generator()
        x_b64 = x.to_b64()
        y = cls()
        y.set_b64(x_b64)
        y_p = y.from_b64(x_b64)
        self.assertIs(x == y == y_p, True)

    def _testSetRandom(self, cls):
        x = cls()
        x.set_random()
        self.assertIs(x.is_zero(), False)
        y = cls()
        y.set_random()
        self.assertIs(x == y, False)
        self.assertNotEqual(x.get_str(), y.get_str())


class TestG1(GBaseTest):
    def testByteSize(self):
        self._testByteSize(G1, 48)

    def testStr(self):
        self._testStr(G1)

    def testBytes(self):
        self._testBytes(G1)

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

    def testBytes(self):
        self._testBytes(G2)

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
        s = "1 2 3 4 5 6 7 8 9 10 11 12"
        x = GT()
        x.set_str(s)
        y = GT.from_str(s)
        self.assertEqual(x.get_str(), s)
        self.assertEqual(y.get_str(), s)

    def testBytes(self):
        x = GT.from_str("1 2 3 4 5 6 7 8 9 10 11 12")
        x_b = x.to_bytes()
        y = GT()
        y.set_bytes(x_b)
        z = GT.from_bytes(x_b)
        self.assertEqual(x.get_str(), y.get_str())
        self.assertEqual(x.get_str(), z.get_str())

    def testInt(self):
        i = 42
        x = GT()
        x.set_int(i)
        y = GT.from_int(i)
        self.assertEqual(x.get_str(), "42 0 0 0 0 0 0 0 0 0 0 0")
        self.assertEqual(x.get_str(), y.get_str())

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
        x = GT.from_int(42)
        x_i = x.inv()
        x_ii = ~x
        self.assertIs(x_i == x_ii, True)
        x_p = ~x_i
        self.assertIs(x_p == x, True)

    def testPairingAndPow(self):
        a = Fr.from_int(123)
        b = Fr.from_int(456)
        P = G1.from_hash(b"1")
        Q = G2.from_hash(b"1")
        aP = P * a
        bQ = Q * b
        e = GT.pairing(P, Q)
        e1 = e**a
        e2 = GT.pairing(aP, Q)
        self.assertIs(e1 == e2, True)
        e1 = e**b
        e2 = GT.pairing(P, bQ)
        self.assertIs(e1 == e2, True)
        n = Fr.from_int(3)
        e1 = e**n
        e2 = e * e * e
        self.assertIs(e1 == e2, True)

    def testSerialization(self):
        self._testSerialization(GT)

    def testFile(self):
        self._testFile(GT)

    def testB64(self):
        self._testB64(GT)

    def testPowVec(self):
        n = 3
        e = (GT * n)()
        s = (Fr * n)()
        e[0].set_object(GT.pairing(G1.from_hash(b"1"), G2.from_hash(b"1")))
        e[1].set_object(GT.pairing(G1.from_hash(b"2"), G2.from_hash(b"2")))
        e[2].set_object(GT.pairing(G1.from_hash(b"3"), G2.from_hash(b"3")))
        s[0].set_object(Fr.from_random())
        s[1].set_object(Fr.from_random())
        s[2].set_object(Fr.from_random())
        E = GT.from_int(1)
        for i in range(n):
            E *= e[i] ** s[i]
        EE = GT.pown(e, s)
        self.assertIs(E == EE, True)


if __name__ == "__main__":
    unittest.main()
