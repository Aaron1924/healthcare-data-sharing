import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.utils.helpers import B64Mixin, InfoMixin, JoinMixin, ReprMixin
from pygroupsig.utils.mcl import G1, G2, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    g1: G1
    g2: G2
    h1: G1
    h2: G1
    ipk: G2

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    isk: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    A: G1
    x: Fr
    y: Fr
    s: Fr
    H: G1
    h2s: G1

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    AA: G1
    A_: G1
    d: G1
    pi: spk.GeneralRepresentationProof
    nym: G1

class DL21(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    def setup(self) -> None: ...
    def join_mgr(
        self, message: dict[str, str] | None = None
    ) -> dict[str, str]: ...
    def join_mem(
        self, message: dict[str, str], key: MemberKey
    ) -> dict[str, str]: ...
    def sign(
        self, message: str, key: MemberKey, scope: str = "def"
    ) -> dict[str, str]: ...
    def verify(
        self, message: str, signature: str, scope: str = "def"
    ) -> dict[str, str]: ...
    def identify(
        self, signature: str, key: MemberKey, scope: str = "def"
    ) -> dict[str, str]: ...
    def link(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        key: MemberKey,
        scope: str = "def",
    ) -> dict[str, str]: ...
    def link_verify(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        proof: str,
        scope: str = "def",
    ) -> dict[str, str]: ...
