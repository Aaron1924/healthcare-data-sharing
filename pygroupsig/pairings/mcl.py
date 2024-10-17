import ctypes
import logging
from base64 import b64decode, b64encode

import pygroupsig.pairings.utils as ut


class Base(ctypes.Structure):
    # ffi/go/lib/lib.go
    BUF_SZ = 2048
    SIG = "mclBn{}_{}"

    def __str__(self):
        return f"{self.__class__} {self.get_str()}"

    def __repr__(self):
        return str(self)

    def is_zero(self):
        return bool(self._no_args("isZero"))

    def __eq__(self, y):
        return bool(self._one_arg("isEqual", y))

    def is_equal(self, y):
        return self.__eq__(y)

    def __neg__(self):
        return self._no_args("neg", ret=True)

    def neg(self):
        return self.__neg__()

    def __add__(self, y):
        return self._one_arg("add", y, ret=True)

    def add(self, y):
        return self.__add__(y)

    def __sub__(self, y):
        return self._one_arg("sub", y, ret=True)

    def sub(self, y):
        return self.__sub__(y)

    def __mul__(self, y):
        return self._one_arg("mul", y, ret=True)

    def mul(self, y):
        return self.__mul__(y)

    def to_bytes(self):
        func = self._func(
            "serialize",
            [
                ctypes.c_char * self.BUF_SZ,
                ctypes.c_size_t,
                ctypes.POINTER(self.__class__),
            ],
            ctypes.c_size_t,
        )
        buf = ctypes.create_string_buffer(self.BUF_SZ)
        sz = func(buf, self.BUF_SZ, self)
        return buf.raw[:sz]

    def set_bytes(self, buf):
        func = self._func(
            "deserialize",
            [
                ctypes.POINTER(self.__class__),
                ctypes.c_char_p,
                ctypes.c_size_t,
            ],
            ctypes.c_size_t,
        )
        func(self, buf, len(buf))

    @classmethod
    def from_bytes(cls, buf):
        ret = cls()
        ret.set_bytes(buf)
        return ret

    def to_hex(self):
        return "".join([f"{b:02x}" for b in self.to_bytes()])

    def to_b64(self):
        return b64encode(self.to_bytes()).decode()

    def set_b64(self, s):
        return self.set_bytes(b64decode(s.encode()))

    @classmethod
    def from_b64(cls, s):
        return cls.from_bytes(b64decode(s.encode()))

    def set_object(self, y):
        return self.set_bytes(y.to_bytes())

    @classmethod
    def from_object(cls, y):
        return cls.from_bytes(y.to_bytes())

    @classmethod
    def byte_size(cls):
        func = getattr(ut.lib, f"mclBn_get{cls.__name__}ByteSize")
        func.restype = ctypes.c_int
        return func()

    def to_file(self, file):
        with open(file, "wb") as f:
            f.write(self.to_b64())

    def set_file(self, file):
        with open(file, "rb") as f:
            return self.set_b64(f.read())

    @classmethod
    def from_file(cls, file):
        with open(file, "rb") as f:
            return cls.from_b64(f.read())

    def _one_arg(self, fn, y, ret=False):
        argtypes = [ctypes.POINTER(self.__class__)] * 2
        restype = ctypes.c_int
        if ret:
            argtypes.append(ctypes.POINTER(self.__class__))
            restype = None
        func = self._func(fn, argtypes, restype)
        if ret:
            ret = self.__class__()
            func(ret, self, y)
            return ret
        else:
            return func(self, y)

    def _no_args(self, fn, ret=False):
        argtypes = [ctypes.POINTER(self.__class__)]
        restype = ctypes.c_int
        if ret:
            argtypes.append(ctypes.POINTER(self.__class__))
            restype = None
        func = self._func(fn, argtypes, restype)
        if ret:
            ret = self.__class__()
            func(ret, self)
            return ret
        else:
            return func(self)

    def _func(self, fn, argtypes, restype=None):
        func = getattr(ut.lib, self.SIG.format(self.__class__.__name__, fn))
        func.argtypes = argtypes
        func.restype = restype
        return func


class StrMixin:
    def set_str(self, s, mode=10):
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        func = self._func(
            "setStr",
            [
                ctypes.POINTER(self.__class__),
                ctypes.c_char_p,
                ctypes.c_size_t,
                ctypes.c_int,
            ],
            ctypes.c_int,
        )
        if func(self, s, len(s), mode):
            raise RuntimeError(
                f"Failed to call {self.__class__.__name__}.setStr()"
            )

    @classmethod
    def from_str(cls, s, mode=10):
        ret = cls()
        ret.set_str(s, mode)
        return ret

    def get_str(self, mode=10):
        buf = ctypes.create_string_buffer(self.BUF_SZ)
        func = self._func(
            "getStr",
            [
                ctypes.c_char * self.BUF_SZ,
                ctypes.c_size_t,
                ctypes.POINTER(self.__class__),
                ctypes.c_int,
            ],
            ctypes.c_int,
        )
        if not func(buf, self.BUF_SZ, self, mode):
            raise RuntimeError(
                f"Failed to call {self.__class__.__name__}.getStr()"
            )
        return buf.value.decode()


class HashEndianPrngCmpMixin:
    def set_hash(self, s):
        if isinstance(s, str):
            s = bytes(bytearray.fromhex(s))
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        func = self._func(
            "setHashOf",
            [
                ctypes.POINTER(self.__class__),
                ctypes.c_char_p,
                ctypes.c_size_t,
            ],
            ctypes.c_int,
        )
        if func(self, s, len(s)):
            raise RuntimeError(
                f"Failed to call {self.__class__.__name__}.setHashOf()"
            )

    @classmethod
    def from_hash(cls, s):
        ret = cls()
        ret.set_hash(s)
        return ret

    # def set_little_endian(self, s):
    #     if isinstance(s, str):
    #         s = s.encode()
    #     elif not isinstance(s, bytes):
    #         print(
    #             f"Error: Invalid input type {s}, expected str/bytes"
    #         )
    #         exit(1)
    #     func = self._func(
    #         "setLittleEndianHashOf",
    #         [
    #             ctypes.POINTER(self.__class__),
    #             ctypes.c_char_p,
    #             ctypes.c_size_t,
    #         ],
    #         ctypes.c_int,
    #     )
    #     func(self, s, len(s))

    # from_unformat_bytes = set_little_endian

    def set_random(self):
        func = self._func(
            "setByCSPRNG",
            [ctypes.POINTER(self.__class__)],
            ctypes.c_int,
        )
        if func(self):
            raise RuntimeError(
                f"Failed to {self.__class__.__name__}.setByCSPNRG()"
            )

    @classmethod
    def from_random(cls):
        ret = cls()
        ret.set_random()
        return ret

    def cmp(self, y):
        return self._one_arg("cmp", y)

    def __gt__(self, y):
        return self._one_arg("cmp", y) == 1

    def __ge__(self, y):
        return self.__gt__(y) or self.__eq__(y)

    def __lt__(self, y):
        return self._one_arg("cmp", y) == -1

    def __le__(self, y):
        return self.__lt__(y) or self.__eq__(y)


class OneInvDivMixin:
    def is_one(self):
        return bool(self._no_args("isOne"))

    def __invert__(self):
        return self._no_args("inv", ret=True)

    def inv(self):
        return self.__invert__()

    def __truediv__(self, y):
        return self._one_arg("div", y, ret=True)

    def div(self, y):
        return self.__truediv__(y)


class MulFrMixin:
    def __mul__(self, y):
        func = self._func(
            "mul", [ctypes.POINTER(self.__class__)] * 2 + [ctypes.POINTER(Fr)]
        )
        ret = self.__class__()
        func(ret, self, y)
        return ret

    def mul(self, y):
        return self.__mul__(y)


class MulVecMixin:
    def muln(self, x, y):
        if len(x) != len(y):
            logging.warn(f"muln: len(x)={len(x)} != len(y)={len(y)}")
        func = self._func(
            "mulVec",
            [ctypes.POINTER(self.__class__)] * 2
            + [ctypes.POINTER(Fr), ctypes.c_size_t],
        )
        func(self, x, y, min(len(x), len(y)))


class PowMixin:
    def __pow__(self, y):
        return self._one_arg("pow", y, ret=True)

    def pow(self, y):
        return self.__pow__(y)


class PowFrMixin:
    def __pow__(self, y):
        func = self._func(
            "pow", [ctypes.POINTER(self.__class__)] * 2 + [ctypes.POINTER(Fr)]
        )
        ret = self.__class__()
        func(ret, self, y)
        return ret

    def pow(self, y):
        return self.__mul__(y)


class HashAndMapMixin:
    def set_hash(self, s):
        if isinstance(s, str):
            s = bytes(bytearray.fromhex(s))
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        func = self._func(
            "hashAndMapTo",
            [
                ctypes.POINTER(self.__class__),
                ctypes.c_char_p,
                ctypes.c_size_t,
            ],
            ctypes.c_int,
        )
        if func(self, s, len(s)):
            raise RuntimeError(
                f"Failed to call {self.__class__.__name__}.hashAndMapTo()"
            )

    @classmethod
    def from_hash(cls, s):
        ret = cls()
        ret.set_hash(s)
        return ret


class IntMixin:
    def set_int(self, i):
        if not isinstance(i, int):
            raise TypeError(f"Invalid {i} type. Expected int")
        func = self._func(
            "setInt", [ctypes.POINTER(self.__class__), ctypes.c_int64]
        )
        func(self, i)

    @classmethod
    def from_int(cls, i):
        ret = cls()
        ret.set_int(i)
        return ret


class GenPrngMixin:
    def set_random(self):
        gen = self.__class__()
        if isinstance(gen, G1):
            gen.set_str(ut.BLS12_381_P)
        else:
            gen.set_str(ut.BLS12_381_Q)
        r = Fr()
        r.set_random()
        self.set_object(gen * r)

    @classmethod
    def from_random(cls):
        ret = cls()
        ret.set_random()
        return ret


class Fp(
    StrMixin,
    HashEndianPrngCmpMixin,
    OneInvDivMixin,
    PowMixin,
    IntMixin,
    Base,
):
    _fields_ = [("d", ctypes.c_uint64 * ut.MCLBN_FP_UNIT_SIZE)]


class Fr(
    StrMixin,
    HashEndianPrngCmpMixin,
    OneInvDivMixin,
    PowMixin,
    IntMixin,
    Base,
):
    _fields_ = [("d", ctypes.c_uint64 * ut.MCLBN_FR_UNIT_SIZE)]


class Fp2(OneInvDivMixin, Base):
    D = 2
    _fields_ = [("d", Fp * D)]

    @classmethod
    def byte_size(cls):
        return Fp.byte_size() * cls.D


class G1(
    StrMixin, MulFrMixin, MulVecMixin, HashAndMapMixin, GenPrngMixin, Base
):
    _fields_ = [("x", Fp), ("y", Fp), ("z", Fp)]


class G2(
    StrMixin, MulFrMixin, MulVecMixin, HashAndMapMixin, GenPrngMixin, Base
):
    _fields_ = [("x", Fp2), ("y", Fp2), ("z", Fp2)]


class GT(StrMixin, OneInvDivMixin, MulVecMixin, PowFrMixin, IntMixin, Base):
    D = 12
    _fields_ = [("d", Fp * D)]

    @classmethod
    def byte_size(cls):
        return Fp.byte_size() * cls.D

    def pown(self, x, y):
        if len(x) != len(y):
            logging.warn(f"pown: len(x)={len(x)} != len(y)={len(y)}")
        func = self._func(
            "powVec",
            [ctypes.POINTER(self.__class__)] * 2
            + [ctypes.POINTER(Fr), ctypes.c_size_t],
        )
        func(self, x, y, min(len(x), len(y)))

    @classmethod
    def pairing(cls, e1, e2):
        func = getattr(ut.lib, "mclBn_pairing")
        func.argtypes = [
            ctypes.POINTER(cls),
            ctypes.POINTER(G1),
            ctypes.POINTER(G2),
        ]
        ret = cls()
        func(ret, e1, e2)
        return ret
