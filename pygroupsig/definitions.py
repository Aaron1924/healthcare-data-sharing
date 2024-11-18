import json
from base64 import b64decode

from pygroupsig.schemes.bbs04 import BBS04
from pygroupsig.schemes.bbs04 import GroupKey as BBS04GrpKey
from pygroupsig.schemes.bbs04 import ManagerKey as BBS04MgrKey
from pygroupsig.schemes.bbs04 import MemberKey as BBS04MemKey
from pygroupsig.schemes.bbs04 import Signature as BBS04Signature
from pygroupsig.schemes.cpy06 import CPY06
from pygroupsig.schemes.cpy06 import GroupKey as CPY06GrpKey
from pygroupsig.schemes.cpy06 import ManagerKey as CPY06MgrKey
from pygroupsig.schemes.cpy06 import MemberKey as CPY06MemKey
from pygroupsig.schemes.cpy06 import Signature as CPY06Signature
from pygroupsig.schemes.dl21 import DL21
from pygroupsig.schemes.dl21 import GroupKey as DL21GrpKey
from pygroupsig.schemes.dl21 import ManagerKey as DL21MgrKey
from pygroupsig.schemes.dl21 import MemberKey as DL21MemKey
from pygroupsig.schemes.dl21 import Signature as DL21Signature
from pygroupsig.schemes.dl21seq import DL21SEQ
from pygroupsig.schemes.dl21seq import GroupKey as DL21SEQGrpKey
from pygroupsig.schemes.dl21seq import ManagerKey as DL21SEQMgrKey
from pygroupsig.schemes.dl21seq import MemberKey as DL21SEQMemKey
from pygroupsig.schemes.dl21seq import Signature as DL21SEQSignature
from pygroupsig.schemes.gl19 import GL19
from pygroupsig.schemes.gl19 import BlindKey as GL19BlindKey
from pygroupsig.schemes.gl19 import GroupKey as GL19GrpKey
from pygroupsig.schemes.gl19 import ManagerKey as GL19MgrKey
from pygroupsig.schemes.gl19 import MemberKey as GL19MemKey
from pygroupsig.schemes.gl19 import Signature as GL19Signature
from pygroupsig.schemes.klap20 import KLAP20
from pygroupsig.schemes.klap20 import GroupKey as KLAP20GrpKey
from pygroupsig.schemes.klap20 import ManagerKey as KLAP20MgrKey
from pygroupsig.schemes.klap20 import MemberKey as KLAP20MemKey
from pygroupsig.schemes.klap20 import Signature as KLAP20Signature
from pygroupsig.schemes.ps16 import PS16
from pygroupsig.schemes.ps16 import GroupKey as PS16GrpKey
from pygroupsig.schemes.ps16 import ManagerKey as PS16MgrKey
from pygroupsig.schemes.ps16 import MemberKey as PS16MemKey
from pygroupsig.schemes.ps16 import Signature as PS16Signature

SCHEMES = {
    "klap20": KLAP20,
    "gl19": GL19,
    "ps16": PS16,
    "bbs04": BBS04,
    "dl21": DL21,
    "dl21seq": DL21SEQ,
    "cpy06": CPY06,
}

KEYS = {
    "group": {
        "klap20": KLAP20GrpKey,
        "gl19": GL19GrpKey,
        "ps16": PS16GrpKey,
        "bbs04": BBS04GrpKey,
        "dl21": DL21GrpKey,
        "dl21seq": DL21SEQGrpKey,
        "cpy06": CPY06GrpKey,
    },
    "manager": {
        "klap20": KLAP20MgrKey,
        "gl19": GL19MgrKey,
        "ps16": PS16MgrKey,
        "bbs04": BBS04MgrKey,
        "dl21": DL21MgrKey,
        "dl21seq": DL21SEQMgrKey,
        "cpy06": CPY06MgrKey,
    },
    "member": {
        "klap20": KLAP20MemKey,
        "gl19": GL19MemKey,
        "ps16": PS16MemKey,
        "bbs04": BBS04MemKey,
        "dl21": DL21MemKey,
        "dl21seq": DL21SEQMemKey,
        "cpy06": CPY06MemKey,
    },
    "blind": {
        "gl19": GL19BlindKey,
    },
}

SIGNATURES = {
    "klap20": KLAP20Signature,
    "gl19": GL19Signature,
    "ps16": PS16Signature,
    "bbs04": BBS04Signature,
    "dl21": DL21Signature,
    "dl21seq": DL21SEQSignature,
    "cpy06": CPY06Signature,
}


def group(name):
    _name = name.lower()
    if _name in SCHEMES:
        return SCHEMES[_name]()
    raise ValueError(f"Unknown scheme: {name}")


def _parse_b64(b64):
    if isinstance(b64, str):
        b64 = b64.encode()
    elif not isinstance(b64, bytes):
        raise TypeError("Invalid b64. Expected str/bytes")
    dec = b64decode(b64)
    return json.loads(dec)


def key(name=None, ktype=None, b64=None):
    if b64 is not None:
        data = _parse_b64(b64)
        ret = KEYS[data["type"]][data["scheme"]]()
        ret.set_b64(data["key"])
        return ret
    elif name is not None and ktype is not None:
        _name = name.lower()
        _ktype = ktype.lower()
        if _ktype in KEYS:
            if _name in KEYS[_ktype]:
                return KEYS[_ktype][_name]()
            else:
                raise ValueError(f"Unknown scheme: {name}")
        else:
            raise ValueError(f"Unknown key type: {ktype}")
    else:
        raise ValueError("At least on argument is required: name/ktype or b64")


def signature(name=None, b64=None):
    if b64 is not None:
        data = _parse_b64(b64)
        ret = SIGNATURES[data["scheme"]]()
        ret.set_b64(data["signature"])
        return ret
    elif name is not None:
        _name = name.lower()
        if _name in SIGNATURES:
            return SIGNATURES[_name]()
        else:
            raise ValueError(f"Unknown scheme: {name}")
    else:
        raise ValueError("At least on argument is required: name or b64")


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
