from typing import Type

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.utils.helpers import B64Mixin, InfoMixin, JoinMixin, ReprMixin
from pygroupsig.utils.mcl import G1, G2, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    g1: G1
    g2: G2
    g: G1
    h: G1
    h1: G1
    h2: G1
    h3: G1
    ipk: G2
    cpk: G1
    epk: G1

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    isk: Fr
    csk: Fr
    esk: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    A: G1
    x: Fr
    y: Fr
    s: Fr
    l: int
    d: Fr
    H: G1
    h2s: G1
    h3d: G1
    def __init__(self) -> None: ...

class BlindKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    pk: G1
    sk: Fr
    @classmethod
    def from_random(cls: Type[BlindKey], grpkey: GroupKey) -> BlindKey: ...
    def public(self) -> str: ...

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    AA: G1
    A_: G1
    d: G1
    pi: spk.GeneralRepresentationProof
    nym1: G1
    nym2: G1
    ehy1: G1
    ehy2: G1
    expiration: int

class BlindSignature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    nym1: G1
    nym2: G1
    nym3: G1
    c1: G1
    c2: G1

class GL19(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    LIFETIME: int
    def setup(self) -> None: ...
    def join_mgr(
        self, message: dict[str, str] | None = None
    ) -> dict[str, str]: ...
    def join_mem(
        self, message: dict[str, str], key: MemberKey
    ) -> dict[str, str]: ...
    def sign(self, message: str, key: MemberKey) -> dict[str, str]: ...
    def verify(self, message: str, signature: str) -> dict[str, str]: ...
    def blind(
        self, message: str, signature: str, blind_key: BlindKey | None = None
    ) -> dict[str, str]: ...
    def convert(
        self, blind_signatures: list[str], blind_key_public: str
    ) -> dict[str, str]: ...
    def unblind(
        self, converted_signature: str, blind_key: BlindKey
    ) -> dict[str, str]: ...

def durstenfeld_perm(input_list: list[str]) -> None: ...
