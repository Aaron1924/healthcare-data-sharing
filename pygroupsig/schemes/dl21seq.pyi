from typing import TypeVar

from pygroupsig.schemes.dl21 import DL21 as DL21
from pygroupsig.schemes.dl21 import GroupKey as DL21GroupKey
from pygroupsig.schemes.dl21 import ManagerKey as DL21ManagerKey
from pygroupsig.schemes.dl21 import MemberKey as DL21MemberKey
from pygroupsig.schemes.dl21 import Signature as DL21Signature
from pygroupsig.utils.mcl import G1 as G1
from pygroupsig.utils.mcl import GT as GT
from pygroupsig.utils.mcl import Fr as Fr

T = TypeVar("T")

class FromDL21Mixin:
    @classmethod
    def from_dl21(cls: T, o: DL21) -> T: ...

class GroupKey(FromDL21Mixin, DL21GroupKey): ...
class ManagerKey(FromDL21Mixin, DL21ManagerKey): ...

class MemberKey(FromDL21Mixin, DL21MemberKey):
    k: str
    kk: str

class Signature(FromDL21Mixin, DL21Signature):
    seq: dict[int, str]

class DL21SEQ(DL21):
    def __init__(self) -> None: ...
    def join_mem(
        self,
        message: dict[str, str],
        key: MemberKey,  # type: ignore
    ) -> dict[str, str]: ...
    def sign(  # type: ignore
        self, message: str, key: MemberKey, scope: str = "def", state: int = 0
    ) -> dict[str, str]: ...
    def verify(
        self, message: str, signature: str, scope: str = "def"
    ) -> dict[str, str]: ...
    def seqlink(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        key: MemberKey,
        scope: str = "def",
    ) -> dict[str, str]: ...
    def seqlink_verify(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        proof: str,
        scope: str = "def",
    ) -> dict[str, str]: ...

def prf_compute(key: str, state: int) -> str: ...
