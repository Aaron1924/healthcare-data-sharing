from typing import Any, Type, TypeVar

from typing_extensions import Self

from pygroupsig.utils.helpers import ReprMixin
from pygroupsig.utils.mcl import G1, G2, GT, Fr

T = TypeVar("T")

class B64Mixin:
    def to_b64(self) -> str: ...
    def set_b64(self, s: str | bytes) -> None: ...
    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T: ...
    def set_object(self, y: Self) -> None: ...

class DiscreteLogProof(B64Mixin, ReprMixin):
    c: Fr
    s: Fr

class DiscreteLogProof2(B64Mixin, ReprMixin):
    c: Fr
    s: Fr
    x: list[Fr]

NizkProof = DiscreteLogProof

class GeneralRepresentationProof(B64Mixin, ReprMixin):
    c: Fr
    s: list[Fr]

class PairingHomomorphismProof(B64Mixin, ReprMixin):
    c: Fr
    s: G2

class PairingHomomorphismProof2(B64Mixin, ReprMixin):
    c: Fr
    s: G2
    tau: GT

def general_representation_sign(
    y: list[Any],
    g: list[Any],
    x: list[Fr],
    i: list[tuple[int]],
    prods: list[int],
    b_n: str | bytes,
    manual: bool = False,
) -> GeneralRepresentationProof: ...
def general_representation_verify(
    y: list[Any],
    g: list[Any],
    i: list[tuple[int]],
    prods: list[int],
    proof: GeneralRepresentationProof,
    b_n: str | bytes,
    manual: bool = False,
) -> bool: ...
def discrete_log_sign(
    G: G1, g: G1, x: Fr, b_n: str | bytes
) -> DiscreteLogProof: ...
def discrete_log_verify(
    G: G1, g: G1, proof: DiscreteLogProof, b_n: str | bytes
) -> bool: ...
def pairing_homomorphism_sign(
    g: G1, G: GT, xx: G2, b_n: str | bytes
) -> PairingHomomorphismProof: ...
def pairing_homomorphism_verify(
    g: G1, G: GT, proof: PairingHomomorphismProof, b_n: str | bytes
) -> bool: ...
def pairing_homomorphism_sign2(
    xx: G2, g1: G1, g2: G1, e1: GT, e2: GT, tau: GT, b_n: str | bytes
) -> PairingHomomorphismProof2: ...
def pairing_homomorphism_verify2(
    proof: PairingHomomorphismProof2, g1: G1, g2: G1, e1: GT, b_n: str | bytes
) -> bool: ...
