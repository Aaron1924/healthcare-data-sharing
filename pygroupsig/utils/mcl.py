# mypy: disable-error-code="misc,attr-defined,type-var,operator"

import ctypes
import logging
from base64 import b64decode, b64encode
from typing import Any, Type, TypeVar

from typing_extensions import Self

import pygroupsig.utils.constants as ct

T = TypeVar("T", bound="Base")


class Base(ctypes.Structure):
    # ffi/go/lib/lib.go
    BUFFER_SZ: int = 2048
    MCL: str = "mclBn{}_{}"

    def __str__(self) -> str:
        return f"{self.__class__} {self.get_str()}"

    def __repr__(self) -> str:
        return str(self)

    def is_zero(self) -> bool:
        return bool(self._call("isZero"))

    def __eq__(self, y: Self) -> bool:  # type: ignore
        return bool(self._call("isEqual", y))

    def is_equal(self, y: Self) -> bool:
        return self.__eq__(y)

    def __neg__(self) -> Self:
        return self._call("neg", ret=True)

    def neg(self) -> Self:
        return self.__neg__()

    def __add__(self, y: Self) -> Self:
        return self._call("add", y, ret=True)

    def add(self, y: Self) -> Self:
        return self.__add__(y)

    def __sub__(self, y: Self) -> Self:
        return self._call("sub", y, ret=True)

    def sub(self, y: Self) -> Self:
        return self.__sub__(y)

    def __mul__(self, y: Self) -> Self:
        return self._call("mul", y, ret=True)

    def mul(self, y: Self) -> Self:
        return self.__mul__(y)

    def to_bytes(self) -> bytes:
        func = self._func(
            "serialize",
            [
                ctypes.c_char_p,
                ctypes.c_size_t,
                ctypes.POINTER(self.__class__),
            ],
            ctypes.c_size_t,
        )
        buffer = ctypes.create_string_buffer(self.BUFFER_SZ)
        sz = func(buffer, self.BUFFER_SZ, self)
        return buffer.raw[:sz]

    def set_bytes(self, buffer: bytes) -> None:
        func = self._func(
            "deserialize",
            [
                ctypes.POINTER(self.__class__),
                ctypes.c_char_p,
                ctypes.c_size_t,
            ],
            ctypes.c_size_t,
        )
        func(self, buffer, len(buffer))

    @classmethod
    def from_bytes(cls: Type[T], buffer: bytes) -> T:
        ret = cls()
        ret.set_bytes(buffer)
        return ret

    def to_hex(self) -> str:
        return "".join([f"{b:02x}" for b in self.to_bytes()])

    def to_b64(self) -> str:
        return b64encode(self.to_bytes()).decode()

    def set_b64(self, s: str | bytes) -> None:
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        return self.set_bytes(b64decode(s))

    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_b64(s)
        return ret

    def set_object(self, y: Self) -> None:
        return self.set_bytes(y.to_bytes())

    @classmethod
    def from_object(cls: Type[T], y: T) -> T:
        return cls.from_bytes(y.to_bytes())

    @classmethod
    def byte_size(cls: Type[T]) -> int:
        func = getattr(ct.lib, f"mclBn_get{cls.__name__}ByteSize")
        func.restype = ctypes.c_int
        return func()

    def to_file(self, file: str) -> None:
        with open(file, "w") as f:
            f.write(self.to_b64())

    def set_file(self, file: str) -> None:
        with open(file) as f:
            return self.set_b64(f.read())

    @classmethod
    def from_file(cls: Type[T], file: str) -> T:
        ret = cls()
        ret.set_file(file)
        return ret

    def _call(self, fn: str, y: Self | None = None, ret: bool = False) -> Any:
        argtypes = [ctypes.POINTER(self.__class__)] * (1 if y is None else 2)
        restype = None if ret else ctypes.c_int
        if ret:
            argtypes.append(ctypes.POINTER(self.__class__))
        func = self._func(fn, argtypes, restype)
        if ret:
            obj = self.__class__()
            if y is None:
                func(obj, self)
            else:
                func(obj, self, y)
            return obj
        else:
            if y is None:
                return func(self)
            return func(self, y)

    def _func(
        self, fn: str, argtypes: list[Any], restype: Any | None = None
    ) -> Any:
        func = getattr(ct.lib, self.MCL.format(self.__class__.__name__, fn))
        func.argtypes = argtypes
        func.restype = restype
        return func


# noinspection PyUnresolvedReferences
class StrMixin:
    def set_str(self, s: str | bytes, mode: int = 10) -> None:
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
    def from_str(cls: Type[T], s: str | bytes, mode: int = 10) -> T:
        ret = cls()
        ret.set_str(s, mode)
        return ret

    def get_str(self, mode: int = 10) -> str:
        buf = ctypes.create_string_buffer(self.BUFFER_SZ)
        func = self._func(
            "getStr",
            [
                ctypes.c_char_p,
                ctypes.c_size_t,
                ctypes.POINTER(self.__class__),
                ctypes.c_int,
            ],
            ctypes.c_int,
        )
        if not func(buf, self.BUFFER_SZ, self, mode):
            raise RuntimeError(
                f"Failed to call {self.__class__.__name__}.getStr()"
            )
        return buf.value.decode()


# noinspection PyUnresolvedReferences
class HashRandomCmpMixin:
    def set_hash(self, s: str | bytes) -> None:
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
    def from_hash(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_hash(s)
        return ret

    def set_random(self) -> None:
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
    def from_random(cls: Type[T]) -> T:
        ret = cls()
        ret.set_random()
        return ret

    def cmp(self, y: Self) -> int:
        return self._call("cmp", y)

    def __gt__(self, y: Self) -> bool:
        return self._call("cmp", y) == 1

    def __ge__(self, y: Self) -> bool:
        return self.__gt__(y) or self.__eq__(y)

    def __lt__(self, y: Self) -> bool:
        return self._call("cmp", y) == -1

    def __le__(self, y: Self) -> bool:
        return self.__lt__(y) or self.__eq__(y)


# noinspection PyUnresolvedReferences
class OneInvDivMixin:
    def is_one(self) -> bool:
        return bool(self._call("isOne"))

    def __invert__(self) -> Self:
        return self._call("inv", ret=True)

    def inv(self) -> Self:
        return self.__invert__()

    def __truediv__(self, y: Self) -> Self:
        return self._call("div", y, ret=True)

    def div(self, y: Self) -> Self:
        return self.__truediv__(y)


# noinspection PyUnresolvedReferences
class MulFrMixin:
    def __mul__(self, y: "Fr") -> Self:
        func = self._func(
            "mul", [ctypes.POINTER(self.__class__)] * 2 + [ctypes.POINTER(Fr)]
        )
        ret = self.__class__()
        func(ret, self, y)
        return ret

    def mul(self, y: "Fr") -> Self:
        return self.__mul__(y)


class MulVecMixin:
    @classmethod
    def muln(cls: Type[T], x: ctypes.Array[T], y: ctypes.Array["Fr"]) -> T:
        if len(x) != len(y):
            logging.warn(f"muln: len(x)={len(x)} != len(y)={len(y)}")
        ret = cls()
        func = ret._func(  # noqa
            "mulVec",
            [ctypes.POINTER(cls)] * 2 + [ctypes.POINTER(Fr), ctypes.c_size_t],
        )
        func(ret, x, y, min(len(x), len(y)))
        return ret


# noinspection PyUnresolvedReferences
class PowMixin:
    def __pow__(self, y: Self) -> Self:
        return self._call("pow", y, ret=True)

    def pow(self, y: Self) -> Self:
        return self.__pow__(y)


# noinspection PyUnresolvedReferences
class PowFrMixin:
    def __pow__(self, y: "Fr") -> Self:
        func = self._func(
            "pow", [ctypes.POINTER(self.__class__)] * 2 + [ctypes.POINTER(Fr)]
        )
        ret = self.__class__()
        func(ret, self, y)
        return ret

    def pow(self, y: "Fr") -> Self:
        return self.__pow__(y)


# noinspection PyUnresolvedReferences
class HashAndMapMixin:
    def set_hash(self, s: str | bytes) -> None:
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
    def from_hash(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_hash(s)
        return ret


# noinspection PyUnresolvedReferences
class IntMixin:
    def set_int(self, i: int) -> None:
        if not isinstance(i, int):
            raise TypeError(f"Invalid {i} type. Expected int")
        func = self._func(
            "setInt", [ctypes.POINTER(self.__class__), ctypes.c_int64]
        )
        func(self, i)

    @classmethod
    def from_int(cls: Type[T], i: int) -> T:
        ret = cls()
        ret.set_int(i)
        return ret


# noinspection PyUnresolvedReferences
class GeneratorMixin:
    def set_generator(self) -> None:
        s = ct.BLS12_381_P
        if isinstance(self, G2):
            s = ct.BLS12_381_Q
        self.set_str(s)

    @classmethod
    def from_generator(cls: Type[T]) -> T:
        ret = cls()
        ret.set_generator()
        return ret

    def set_random(self) -> None:
        gen = self.__class__()
        gen.set_generator()
        r = Fr()
        r.set_random()
        self.set_object(gen * r)

    @classmethod
    def from_random(cls: Type[T]) -> T:
        ret = cls()
        ret.set_random()
        return ret


class Fp(
    StrMixin,
    HashRandomCmpMixin,
    OneInvDivMixin,
    PowMixin,
    IntMixin,
    Base,
):
    _fields_ = [("d", ctypes.c_uint64 * ct.MCLBN_FP_UNIT_SIZE)]  # noqa


class Fr(
    StrMixin,
    HashRandomCmpMixin,
    OneInvDivMixin,
    PowMixin,
    IntMixin,
    Base,
):
    _fields_ = [("d", ctypes.c_uint64 * ct.MCLBN_FR_UNIT_SIZE)]  # noqa


class Fp2(OneInvDivMixin, Base):
    D: int = 2
    _fields_ = [("d", Fp * D)]

    @classmethod
    def byte_size(cls: Type[T]) -> int:
        return Fp.byte_size() * cls.D


class G1(
    StrMixin,
    MulFrMixin,
    MulVecMixin,
    HashAndMapMixin,
    GeneratorMixin,
    Base,
):
    _fields_ = [("x", Fp), ("y", Fp), ("z", Fp)]


class G2(
    StrMixin,
    MulFrMixin,
    MulVecMixin,
    HashAndMapMixin,
    GeneratorMixin,
    Base,
):
    _fields_ = [("x", Fp2), ("y", Fp2), ("z", Fp2)]


class GT(StrMixin, OneInvDivMixin, MulVecMixin, PowFrMixin, IntMixin, Base):
    D: int = 12
    _fields_ = [("d", Fp * D)]

    @classmethod
    def byte_size(cls: Type[T]) -> int:
        return Fp.byte_size() * cls.D

    @classmethod
    def pown(cls: Type[T], x: ctypes.Array[T], y: ctypes.Array["Fr"]) -> T:
        if len(x) != len(y):
            logging.warn(f"pown: len(x)={len(x)} != len(y)={len(y)}")
        ret = cls()
        func = ret._func(  # noqa
            "powVec",
            [ctypes.POINTER(cls)] * 2 + [ctypes.POINTER(Fr), ctypes.c_size_t],
        )
        func(ret, x, y, min(len(x), len(y)))
        return ret

    @classmethod
    def pairing(cls: Type[T], e1: "G1", e2: "G2") -> T:
        func = getattr(ct.lib, "mclBn_pairing")
        func.argtypes = [
            ctypes.POINTER(cls),
            ctypes.POINTER(G1),
            ctypes.POINTER(G2),
        ]
        ret = cls()
        func(ret, e1, e2)
        return ret
