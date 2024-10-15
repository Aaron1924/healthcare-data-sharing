from pygroupsig.klap20.scheme import (
    Klap20,
    GroupKey as Klap20GrpKey,
    ManagerKey as Klap20MgrKey,
    MemberKey as Klap20MemKey,
    Signature as Klap20Signature,
)
from pygroupsig.gl19.scheme import (
    Gl19,
    GroupKey as Gl19GrpKey,
    ManagerKey as Gl19MgrKey,
    MemberKey as Gl19MemKey,
    Signature as Gl19Signature,
)
from pygroupsig.ps16.scheme import (
    Ps16,
    GroupKey as Ps16GrpKey,
    ManagerKey as Ps16MgrKey,
    MemberKey as Ps16MemKey,
    Signature as Ps16Signature,
)
import json
from base64 import b64decode
import logging


class Scheme:
    _SCHEMES = {
        "klap20": Klap20,
        "gl19": Gl19,
        "ps16": Ps16,
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
        },
        "manager": {
            "klap20": Klap20MgrKey,
            "gl19": Gl19MgrKey,
            "ps16": Ps16MgrKey,
        },
        "member": {
            "klap20": Klap20MemKey,
            "gl19": Gl19MemKey,
            "ps16": Ps16MemKey,
        }
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


class OpenMixin:
    ...


class OVerifyMixin:
    ...


class RevealTraceClaimCVerifyProveEqPEqVerifyMixin:
    ...


class BlindConvertUnblindMixin:
    ...


class IdentifyLinkLVerifyMixin:
    ...


class SeqlinkSVerifyMixin:
    ...
