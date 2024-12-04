import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.utils.helpers import (
    GML,
    B64Mixin,
    InfoMixin,
    JoinMixin,
    ReprMixin,
)
from pygroupsig.utils.mcl import G1, G2, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    g: G1
    gg: G2
    XX: G2
    YY: G2
    ZZ0: G2
    ZZ1: G2

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    x: Fr
    y: Fr
    z0: Fr
    z1: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    alpha: Fr
    u: G1
    v: G1
    w: G1

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    uu: G1
    vv: G1
    ww: G1
    pi: spk.DiscreteLogProof

class KLAP20(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    gml: GML
    def setup(self) -> None: ...
    def join_mgr(
        self, message: dict[str, str] | None = None
    ) -> dict[str, str]: ...
    def join_mem(
        self, message: dict[str, str], key: MemberKey
    ) -> dict[str, str]: ...
    def sign(self, message: str, key: MemberKey) -> dict[str, str]: ...
    def verify(self, message: str, signature: str) -> dict[str, str]: ...
    def open(self, signature: str) -> dict[str, str]: ...
    def open_verify(self, signature: str, proof: str) -> dict[str, str]: ...
