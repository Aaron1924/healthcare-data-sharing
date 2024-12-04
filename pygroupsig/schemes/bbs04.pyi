from pygroupsig.interfaces import ContainerInterface as ContainerInterface
from pygroupsig.interfaces import SchemeInterface as SchemeInterface
from pygroupsig.utils.helpers import GML, B64Mixin, InfoMixin, JoinMixin
from pygroupsig.utils.helpers import ReprMixin as ReprMixin
from pygroupsig.utils.mcl import G1, G2, GT, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    g1: G1
    g2: G2
    h: G1
    u: G1
    v: G1
    w: G2
    hw: GT
    hg2: GT
    g1g2: GT

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    xi1: Fr
    xi2: Fr
    gamma: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    x: Fr
    A: G1
    Ag2: GT

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    T1: G1
    T2: G1
    T3: G1
    c: Fr
    salpha: Fr
    sbeta: Fr
    sx: Fr
    sdelta1: Fr
    sdelta2: Fr

class BBS04(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    gml: GML
    def setup(self) -> None: ...
    def join_seq(self) -> int: ...
    def join_mgr(
        self, message: dict[str, str] | None = None
    ) -> dict[str, str]: ...
    def join_mem(
        self, message: dict[str, str], key: MemberKey
    ) -> dict[str, str]: ...
    def sign(self, message: str, key: MemberKey) -> dict[str, str]: ...
    def verify(self, message: str, signature: str) -> dict[str, str]: ...
    def open(self, signature: Signature) -> dict[str, str]: ...
