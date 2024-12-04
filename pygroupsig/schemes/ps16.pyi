from typing import Any

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface
from pygroupsig.interfaces import SchemeInterface as SchemeInterface
from pygroupsig.utils.helpers import B64Mixin, InfoMixin, JoinMixin
from pygroupsig.utils.helpers import ReprMixin as ReprMixin
from pygroupsig.utils.mcl import G1, G2, Fr

class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    g: G1
    gg: G2
    X: G2
    Y: G2

class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    x: Fr
    y: Fr

class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    sk: Fr
    sigma1: G1
    sigma2: G1

class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    sigma1: G1
    sigma2: G1
    pi: spk.DiscreteLogProof

class PS16(JoinMixin, ReprMixin, SchemeInterface[MemberKey]):
    gml: dict[str, tuple[Any]]
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
