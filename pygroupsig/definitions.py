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
    "bbs04": (BBS04, BBS04GrpKey, BBS04MgrKey, BBS04MemKey, BBS04Signature),
    "ps16": (PS16, PS16GrpKey, PS16MgrKey, PS16MemKey, PS16Signature),
    "cpy06": (CPY06, CPY06GrpKey, CPY06MgrKey, CPY06MemKey, CPY06Signature),
    "klap20": (
        KLAP20,
        KLAP20GrpKey,
        KLAP20MgrKey,
        KLAP20MemKey,
        KLAP20Signature,
    ),
    "gl19": (
        GL19,
        GL19GrpKey,
        GL19MgrKey,
        GL19MemKey,
        GL19BlindKey,
        GL19Signature,
    ),
    "dl21": (DL21, DL21GrpKey, DL21MgrKey, DL21MemKey, DL21Signature),
    "dl21seq": (
        DL21SEQ,
        DL21SEQGrpKey,
        DL21SEQMgrKey,
        DL21SEQMemKey,
        DL21SEQSignature,
    ),
}


def group(name):
    name_ = name.lower()
    try:
        return SCHEMES[name_][0]()
    except KeyError:
        raise ValueError(f"Unknown scheme: {name}") from None


def _parse_b64(b64):
    if isinstance(b64, str):
        b64 = b64.encode()
    elif not isinstance(b64, bytes):
        raise TypeError("Invalid b64. Expected str/bytes")
    dec = b64decode(b64)
    return json.loads(dec)


def _parse_key(name, ktype):
    try:
        sch_data = SCHEMES[name]
    except KeyError:
        raise ValueError(f"Unknown scheme: {name}") from None
    keys = sch_data[1 : len(sch_data) - 1]
    key_types = [k.__name__.split("Key")[0].lower() for k in keys]
    try:
        return keys[key_types.index(ktype)]()
    except ValueError:
        raise ValueError(f"Unknown key type: {ktype}") from None


def key(name=None, ktype=None, b64=None):
    if b64 is not None:
        data = _parse_b64(b64)
        ret = _parse_key(data["scheme"], data["type"])
        ret.set_b64(data["key"])
        return ret
    elif name is not None and ktype is not None:
        return _parse_key(name.lower(), ktype.lower())
    else:
        raise ValueError("At least on argument is required: name/ktype or b64")


def _parse_signature(name):
    try:
        sch_data = SCHEMES[name]
    except KeyError:
        raise ValueError(f"Unknown scheme: {name}") from None
    return sch_data[-1]()


def signature(name=None, b64=None):
    if b64 is not None:
        data = _parse_b64(b64)
        ret = _parse_signature(data["scheme"])
        ret.set_b64(data["signature"])
        return ret
    elif name is not None:
        return _parse_signature(name.lower())
    else:
        raise ValueError("At least on argument is required: name or b64")
