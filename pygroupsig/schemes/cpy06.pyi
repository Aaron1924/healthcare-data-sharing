from pygroupsig.interfaces import ContainerInterface
from pygroupsig.interfaces import SchemeInterface as SchemeInterface
from pygroupsig.utils.helpers import CRL, GML, B64Mixin, InfoMixin, JoinMixin
from pygroupsig.utils.helpers import ReprMixin as ReprMixin
from pygroupsig.utils.mcl import G1, G2, GT, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    q: G1
    r: G2
    w: G2
    x: G1
    y: G1
    z: G1
    e1: GT
    e2: GT
    e3: GT
    e4: GT
    e5: GT

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    xi1: Fr
    xi2: Fr
    gamma: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    x: Fr
    t: Fr
    A: G1

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    T1: G1
    T2: G1
    T3: G1
    T4: G2
    T5: GT
    c: Fr
    sr1: Fr
    sr2: Fr
    sd1: Fr
    sd2: Fr
    sx: Fr
    st: Fr

class CPY06(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    gml: GML
    crl: CRL
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
    def reveal(self, mem_id: str) -> dict[str, str]: ...
    def trace(self, signature: str) -> dict[str, str]: ...
    def prove_equality(
        self, signatures: list[str], key: MemberKey
    ) -> dict[str, str]: ...
    def prove_equality_verify(
        self, signatures: list[str], proof: str
    ) -> dict[str, str]: ...
    def claim(self, signature: str, key: MemberKey) -> dict[str, str]: ...
    def claim_verify(self, signature: str, proof: str) -> dict[str, str]: ...
