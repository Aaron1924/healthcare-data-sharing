import json
import logging
from base64 import b64decode

from pygroupsig.schemes.bbs04 import Bbs04
from pygroupsig.schemes.bbs04 import GroupKey as Bbs04GrpKey
from pygroupsig.schemes.bbs04 import ManagerKey as Bbs04MgrKey
from pygroupsig.schemes.bbs04 import MemberKey as Bbs04MemKey
from pygroupsig.schemes.bbs04 import Signature as Bbs04Signature
from pygroupsig.schemes.dl21 import Dl21
from pygroupsig.schemes.dl21 import GroupKey as Dl21GrpKey
from pygroupsig.schemes.dl21 import ManagerKey as Dl21MgrKey
from pygroupsig.schemes.dl21 import MemberKey as Dl21MemKey
from pygroupsig.schemes.dl21 import Signature as Dl21Signature
from pygroupsig.schemes.gl19 import Gl19
from pygroupsig.schemes.gl19 import GroupKey as Gl19GrpKey
from pygroupsig.schemes.gl19 import ManagerKey as Gl19MgrKey
from pygroupsig.schemes.gl19 import MemberKey as Gl19MemKey
from pygroupsig.schemes.gl19 import Signature as Gl19Signature
from pygroupsig.schemes.klap20 import GroupKey as Klap20GrpKey
from pygroupsig.schemes.klap20 import Klap20
from pygroupsig.schemes.klap20 import ManagerKey as Klap20MgrKey
from pygroupsig.schemes.klap20 import MemberKey as Klap20MemKey
from pygroupsig.schemes.klap20 import Signature as Klap20Signature
from pygroupsig.schemes.ps16 import GroupKey as Ps16GrpKey
from pygroupsig.schemes.ps16 import ManagerKey as Ps16MgrKey
from pygroupsig.schemes.ps16 import MemberKey as Ps16MemKey
from pygroupsig.schemes.ps16 import Ps16
from pygroupsig.schemes.ps16 import Signature as Ps16Signature


class Scheme:
    _SCHEMES = {
        "klap20": Klap20,
        "gl19": Gl19,
        "ps16": Ps16,
        "bbs04": Bbs04,
        "dl21": Dl21,
    }

    def __new__(cls, scheme):
        _name = scheme.lower()
        if _name in cls._SCHEMES:
            return cls._SCHEMES[_name]()
        raise ValueError(f"Unknown scheme: {scheme}")


class Key:
    _KEYS = {
        "group": {
            "klap20": Klap20GrpKey,
            "gl19": Gl19GrpKey,
            "ps16": Ps16GrpKey,
            "bbs04": Bbs04GrpKey,
            "dl21": Dl21GrpKey,
        },
        "manager": {
            "klap20": Klap20MgrKey,
            "gl19": Gl19MgrKey,
            "ps16": Ps16MgrKey,
            "bbs04": Bbs04MgrKey,
            "dl21": Dl21MgrKey,
        },
        "member": {
            "klap20": Klap20MemKey,
            "gl19": Gl19MemKey,
            "ps16": Ps16MemKey,
            "bbs04": Bbs04MemKey,
            "dl21": Dl21MemKey,
        },
    }

    def __new__(cls, scheme, ktype):
        _name = scheme.lower()
        _ktype = ktype.lower()
        if _ktype in cls._KEYS:
            if _name in cls._KEYS[_ktype]:
                return cls._KEYS[_ktype][_name]()
            else:
                raise ValueError(f"Unknown scheme: {scheme}")
        else:
            raise ValueError(f"Unknown key type: {ktype}")

    @classmethod
    def from_b64(cls, s):
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            msg = "Invalid key type. Expected str/bytes"
            logging.error(msg)
            return msg
        data = json.loads(b64decode(s))
        ret = cls(data["scheme"], data["type"])
        ret.set_b64(data["key"])
        return ret


class Signature:
    _SIGNATURES = {
        "klap20": Klap20Signature,
        "gl19": Gl19Signature,
        "ps16": Ps16Signature,
        "bbs04": Bbs04Signature,
        "dl21": Dl21Signature,
    }

    def __new__(cls, scheme):
        _name = scheme.lower()
        if _name in cls._SIGNATURES:
            return cls._SIGNATURES[_name]()
        else:
            raise ValueError(f"Unknown scheme: {scheme}")

    @classmethod
    def from_b64(cls, s):
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            msg = "Invalid signature type. Expected str/bytes"
            logging.error(msg)
            return msg
        data = json.loads(b64decode(s))
        ret = cls(data["scheme"])
        ret.set_b64(data["signature"])
        return ret


# class SPKDLog:
#     def __init__(self):
#         self.c = Fr()
#         self.s = Fr()

#     def to_b64(self):
#         ret = {"c": self.c.to_b64(), "s": self.s.to_b64()}
#         return b64encode(json.dumps(ret)).decode()

#     @classmethod
#     def from_b64(cls, s):
#         ret = cls()
#         dec = b64decode(s.encode())
#         data = json.loads(dec)
#         ret.c.set_from_b64(data["c"])
#         ret.s.set_from_b64(data["s"])
#         return ret


# class SPKRep:
#     def __init__(self):
#         self.c = Fr()
#         self.s = []


# class SPKPairingHomomorphismG2:
#     def __init__(self):
#         self.c = Fr()
#         self.s = G2()


class OpenMixin: ...


class OVerifyMixin: ...


class RevealTraceClaimCVerifyProveEqPEqVerifyMixin: ...


class BlindConvertUnblindMixin: ...


class IdentifyLinkLVerifyMixin: ...


class SeqlinkSVerifyMixin: ...
