# mypy: disable-error-code="misc"

from typing import Literal, Type, TypeAlias

from typing_extensions import Any, overload

from pygroupsig.interfaces import Container, Scheme
from pygroupsig.schemes.bbs04 import (
    Group as GroupBBS04,
)
from pygroupsig.schemes.bbs04 import (
    GroupKey as GroupKeyBBS04,
)
from pygroupsig.schemes.bbs04 import (
    ManagerKey as ManagerKeyBBS04,
)
from pygroupsig.schemes.bbs04 import (
    MemberKey as MemberKeyBBS04,
)
from pygroupsig.schemes.bbs04 import (
    Signature as SignatureBBS04,
)
from pygroupsig.schemes.cpy06 import (
    Group as GroupCPY06,
)
from pygroupsig.schemes.cpy06 import (
    GroupKey as GroupKeyCPY06,
)
from pygroupsig.schemes.cpy06 import (
    ManagerKey as ManagerKeyCPY06,
)
from pygroupsig.schemes.cpy06 import (
    MemberKey as MemberKeyCPY06,
)
from pygroupsig.schemes.cpy06 import (
    Signature as SignatureCPY06,
)
from pygroupsig.schemes.dl21 import (
    Group as GroupDL21,
)
from pygroupsig.schemes.dl21 import (
    GroupKey as GroupKeyDL21,
)
from pygroupsig.schemes.dl21 import (
    ManagerKey as ManagerKeyDL21,
)
from pygroupsig.schemes.dl21 import (
    MemberKey as MemberKeyDL21,
)
from pygroupsig.schemes.dl21 import (
    Signature as SignatureDL21,
)
from pygroupsig.schemes.dl21seq import (
    Group as GroupDL21SEQ,
)
from pygroupsig.schemes.dl21seq import (
    GroupKey as GroupKeyDL21SEQ,
)
from pygroupsig.schemes.dl21seq import (
    ManagerKey as ManagerKeyDL21SEQ,
)
from pygroupsig.schemes.dl21seq import (
    MemberKey as MemberKeyDL21SEQ,
)
from pygroupsig.schemes.dl21seq import (
    Signature as SignatureDL21SEQ,
)
from pygroupsig.schemes.gl19 import (
    BlindKey as BlindKeyGL19,
)
from pygroupsig.schemes.gl19 import (
    Group as GroupGL19,
)
from pygroupsig.schemes.gl19 import (
    GroupKey as GroupKeyGL19,
)
from pygroupsig.schemes.gl19 import (
    ManagerKey as ManagerKeyGL19,
)
from pygroupsig.schemes.gl19 import (
    MemberKey as MemberKeyGL19,
)
from pygroupsig.schemes.gl19 import (
    Signature as SignatureGL19,
)
from pygroupsig.schemes.klap20 import (
    Group as GroupKLAP20,
)
from pygroupsig.schemes.klap20 import (
    GroupKey as GroupKeyKLAP20,
)
from pygroupsig.schemes.klap20 import (
    ManagerKey as ManagerKeyKLAP20,
)
from pygroupsig.schemes.klap20 import (
    MemberKey as MemberKeyKLAP20,
)
from pygroupsig.schemes.klap20 import (
    Signature as SignatureKLAP20,
)
from pygroupsig.schemes.ps16 import (
    Group as GroupPS16,
)
from pygroupsig.schemes.ps16 import (
    GroupKey as GroupKeyPS16,
)
from pygroupsig.schemes.ps16 import (
    ManagerKey as ManagerKeyPS16,
)
from pygroupsig.schemes.ps16 import (
    MemberKey as MemberKeyPS16,
)
from pygroupsig.schemes.ps16 import (
    Signature as SignaturePS16,
)

SCHEMES: dict[str, Any] = {
    "bbs04": (
        GroupBBS04,
        GroupKeyBBS04,
        ManagerKeyBBS04,
        MemberKeyBBS04,
        SignatureBBS04,
    ),
    "ps16": (
        GroupPS16,
        GroupKeyPS16,
        ManagerKeyPS16,
        MemberKeyPS16,
        SignaturePS16,
    ),
    "cpy06": (
        GroupCPY06,
        GroupKeyCPY06,
        ManagerKeyCPY06,
        MemberKeyCPY06,
        SignatureCPY06,
    ),
    "klap20": (
        GroupKLAP20,
        GroupKeyKLAP20,
        ManagerKeyKLAP20,
        MemberKeyKLAP20,
        SignatureKLAP20,
    ),
    "gl19": (
        GroupGL19,
        GroupKeyGL19,
        ManagerKeyGL19,
        MemberKeyGL19,
        BlindKeyGL19,
        SignatureGL19,
    ),
    "dl21": (
        GroupDL21,
        GroupKeyDL21,
        ManagerKeyDL21,
        MemberKeyDL21,
        SignatureDL21,
    ),
    "dl21seq": (
        GroupDL21SEQ,
        GroupKeyDL21SEQ,
        ManagerKeyDL21SEQ,
        MemberKeyDL21SEQ,
        SignatureDL21SEQ,
    ),
}

# This is so much boilerplate just to have to have static types...
str_BBS04: TypeAlias = Literal["bbs04"]
str_PS16: TypeAlias = Literal["ps16"]
str_CPY06: TypeAlias = Literal["cpy06"]
str_KLAP20: TypeAlias = Literal["klap20"]
str_GL19: TypeAlias = Literal["gl19"]
str_DL21: TypeAlias = Literal["dl21"]
str_DL21SEQ: TypeAlias = Literal["dl21seq"]
str_Group: TypeAlias = Literal["group"]
str_Manager: TypeAlias = Literal["manager"]
str_Member: TypeAlias = Literal["member"]
str_Blind: TypeAlias = Literal["blind"]


@overload
def group(scheme_name: str_BBS04) -> Type[GroupBBS04]: ...
@overload
def group(scheme_name: str_PS16) -> Type[GroupPS16]: ...
@overload
def group(scheme_name: str_CPY06) -> Type[GroupCPY06]: ...
@overload
def group(scheme_name: str_KLAP20) -> Type[GroupKLAP20]: ...
@overload
def group(scheme_name: str_GL19) -> Type[GroupGL19]: ...
@overload
def group(scheme_name: str_DL21) -> Type[GroupDL21]: ...
@overload
def group(scheme_name: str_DL21SEQ) -> Type[GroupDL21SEQ]: ...


def group(scheme_name: str) -> Type[Scheme]:
    try:
        return SCHEMES[scheme_name][0]
    except KeyError:
        raise ValueError(f"Unknown scheme: {scheme_name}")


# BBS04
@overload
def key(scheme_name: str_BBS04, key_type: str_Group) -> Type[GroupKeyBBS04]: ...
@overload
def key(
    scheme_name: str_BBS04, key_type: str_Manager
) -> Type[ManagerKeyBBS04]: ...
@overload
def key(
    scheme_name: str_BBS04, key_type: str_Member
) -> Type[MemberKeyBBS04]: ...


# PS16
@overload
def key(scheme_name: str_PS16, key_type: str_Group) -> Type[GroupKeyPS16]: ...
@overload
def key(
    scheme_name: str_PS16, key_type: str_Manager
) -> Type[ManagerKeyPS16]: ...
@overload
def key(scheme_name: str_PS16, key_type: str_Member) -> Type[MemberKeyPS16]: ...


# CPY06
@overload
def key(scheme_name: str_CPY06, key_type: str_Group) -> Type[GroupKeyCPY06]: ...
@overload
def key(
    scheme_name: str_CPY06, key_type: str_Manager
) -> Type[ManagerKeyCPY06]: ...
@overload
def key(
    scheme_name: str_CPY06, key_type: str_Member
) -> Type[MemberKeyCPY06]: ...


# KLAP20
@overload
def key(
    scheme_name: str_KLAP20, key_type: str_Group
) -> Type[GroupKeyKLAP20]: ...
@overload
def key(
    scheme_name: str_KLAP20, key_type: str_Manager
) -> Type[ManagerKeyKLAP20]: ...
@overload
def key(
    scheme_name: str_KLAP20, key_type: str_Member
) -> Type[MemberKeyKLAP20]: ...


# GL19
@overload
def key(scheme_name: str_GL19, key_type: str_Group) -> Type[GroupKeyGL19]: ...
@overload
def key(
    scheme_name: str_GL19, key_type: str_Manager
) -> Type[ManagerKeyGL19]: ...
@overload
def key(scheme_name: str_GL19, key_type: str_Member) -> Type[MemberKeyGL19]: ...
@overload
def key(scheme_name: str_GL19, key_type: str_Blind) -> Type[BlindKeyGL19]: ...


# DL21
@overload
def key(scheme_name: str_DL21, key_type: str_Group) -> Type[GroupKeyDL21]: ...
@overload
def key(
    scheme_name: str_DL21, key_type: str_Manager
) -> Type[ManagerKeyDL21]: ...
@overload
def key(scheme_name: str_DL21, key_type: str_Member) -> Type[MemberKeyDL21]: ...


# DL21SEQ
@overload
def key(
    scheme_name: str_DL21SEQ, key_type: str_Group
) -> Type[GroupKeyDL21SEQ]: ...
@overload
def key(
    scheme_name: str_DL21SEQ, key_type: str_Manager
) -> Type[ManagerKeyDL21SEQ]: ...
@overload
def key(
    scheme_name: str_DL21SEQ, key_type: str_Member
) -> Type[MemberKeyDL21SEQ]: ...


def key(scheme_name: str, key_type: str) -> Type[Container]:
    try:
        sch_data = SCHEMES[scheme_name]
    except KeyError:
        raise ValueError(f"Unknown scheme: {scheme_name}")
    keys = sch_data[1 : len(sch_data) - 1]
    key_types = [k.__name__.split("Key")[0].lower() for k in keys]
    try:
        return keys[key_types.index(key_type)]
    except ValueError:
        raise ValueError(f"Unknown key type: {key_type}")


@overload
def signature(scheme_name: str_BBS04) -> Type[SignatureBBS04]: ...
@overload
def signature(scheme_name: str_PS16) -> Type[SignaturePS16]: ...
@overload
def signature(scheme_name: str_CPY06) -> Type[SignatureCPY06]: ...
@overload
def signature(scheme_name: str_KLAP20) -> Type[SignatureKLAP20]: ...
@overload
def signature(scheme_name: str_GL19) -> Type[SignatureGL19]: ...
@overload
def signature(scheme_name: str_DL21) -> Type[SignatureDL21]: ...
@overload
def signature(scheme_name: str_DL21SEQ) -> Type[SignatureDL21SEQ]: ...


def signature(scheme_name: str) -> Type[Container]:
    try:
        sch_data = SCHEMES[scheme_name]
    except KeyError:
        raise ValueError(f"Unknown scheme: {scheme_name}")
    return sch_data[-1]
