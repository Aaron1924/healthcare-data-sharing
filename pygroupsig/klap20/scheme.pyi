from pygroupsig.interfaces import KeyInterface, SchemeInterface, SignatureInterface
from pygroupsig.pairings.mcl import Fr, G1, G2

class GroupKey(KeyInterface):
    g: G1
    gg: G2
    XX: G2
    YY: G2
    ZZ0: G2
    ZZ1: G2

class ManagerKey(KeyInterface):
    x: Fr
    y: Fr
    z0: Fr
    z1: Fr

class MemberKey(KeyInterface):
    alpha: Fr
    u: G1
    v: G1
    w: G1

class Signature(SignatureInterface):
    uu: G1
    vv: G1
    ww: G1

class Klap20(SchemeInterface):
    NAME: str
    SEQ: int
    START: int
    grpkey: GroupKey
    mgrkey: ManagerKey
    memkey: MemberKey
    gml: dict[str, tuple[bytes,...]]
    def __init__(self) -> None: ...
    def setup(self) -> None: ...
    def join_mem(self, phase: int, message: dict[str, str] | None = None) -> dict[str, str]: ...
    def join_mgr(self, phase: int, message: dict[str, str] | None = None) -> dict[str, str]: ...
    def sign(self, message: str | bytes) -> dict[str, str]: ...
    def verify(self, message: str | bytes, signature: str) -> dict[str, str]: ...

def spk0_sign(y, g, x, i, prods, b_n): ...
def spk0_verify(y, g, i, prods, pic, pis, b_n): ...
