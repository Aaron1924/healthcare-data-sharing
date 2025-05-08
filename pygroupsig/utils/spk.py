# mypy: disable-error-code="call-arg,assignment,index,operator"

import hashlib
import json
from base64 import b64decode, b64encode
from typing import Any, Type, TypeVar

from typing_extensions import Self

from pygroupsig.utils.helpers import ReprMixin
from pygroupsig.utils.mcl import G1, G2, GT, Fr

T = TypeVar("T")


class B64Mixin:
    def to_b64(self) -> str:
        dump = {}
        for v in vars(self):
            obj = getattr(self, v)
            if isinstance(obj, list):
                dump[v] = [
                    el.to_b64() if not isinstance(el, str) else f"str_{el}"
                    for el in obj
                ]
            else:
                dump[v] = obj.to_b64()
        return b64encode(json.dumps(dump).encode()).decode()

    def set_b64(self, s: str | bytes) -> None:
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        data = json.loads(b64decode(s))
        for k, v in data.items():
            obj = getattr(self, k)
            if isinstance(data[k], list):
                obj.extend(
                    [
                        Fr.from_b64(el)
                        if not el.startswith("str_")
                        else el.split("_")[1]
                        for el in data[k]
                    ]
                )
            else:
                obj.set_b64(data[k])

    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_b64(s)  # type: ignore
        return ret

    def set_object(self, y: Self) -> None:
        for v in vars(y):
            s_obj = getattr(y, v)
            d_obj = getattr(self, v)
            if isinstance(s_obj, list):
                d_obj.extend(s_obj)
            else:
                d_obj.set_object(s_obj)


class DiscreteLogProof(B64Mixin, ReprMixin):
    """Data structure for convenional discrete log proofs"""

    c: Fr
    s: Fr

    def __init__(self) -> None:
        self.c = Fr()
        self.s = Fr()


class DiscreteLogProof2(B64Mixin, ReprMixin):
    """Data structure for convenional discrete log proofs"""

    c: Fr
    s: Fr
    x: list[str]

    def __init__(self) -> None:
        self.c = Fr()
        self.s = Fr()
        self.x = []


# General NIZK proofs of knowledge for CPY06
NizkProof = DiscreteLogProof


class GeneralRepresentationProof(B64Mixin, ReprMixin):
    """Data structure for general representation proofs"""

    c: Fr
    s: list[Fr]

    def __init__(self) -> None:
        self.c = Fr()
        self.s = []


class PairingHomomorphismProof(B64Mixin, ReprMixin):
    """Data structure for pairing homomorphism proofs"""

    c: Fr
    s: G2

    def __init__(self) -> None:
        self.c = Fr()
        self.s = G2()


class PairingHomomorphismProof2(B64Mixin, ReprMixin):
    """Data structure for pairing homomorphism proofs"""

    c: Fr
    s: G2
    tau: GT

    def __init__(self) -> None:
        self.c = Fr()
        self.s = G2()
        self.tau = GT()


def general_representation_sign(
    y: list[Any],
    g: list[Any],
    x: list[Fr],
    i: list[tuple[int, int]],
    prods: list[int],
    b_n: str | bytes,
    manual: bool = False,
) -> GeneralRepresentationProof:
    r = [Fr.from_random() for _ in x]

    ## Compute the challenges according to the relations defined by
    ## the i indexes
    gr = [g[j[1]] * r[j[0]] for j in i]

    ## Compute the challenge products
    prod = []
    if not manual:
        idx = 0
        for j in range(len(y)):
            prod.append(gr[idx])
            idx += 1
            if prods[j] > 1:
                ## We use prods to specify how the i indexes are 'assigned' per
                ## random 'challenge'
                for k in range(prods[j] - 1):
                    prod[j] = prod[j] + gr[idx]
                    idx += 1
    else:
        for j in range(4):
            prod.append(gr[j])
        prod.append(gr[4] + gr[5])
        prod.append(gr[6] + gr[7])

    ## Compute the hash:
    ## pi->c = Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = g[i[j,2]]^r[i[j,1]]
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    # print("bn sign: ", b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    ## Convert the hash to an integer
    proof = GeneralRepresentationProof()
    proof.c.set_hash(h.digest())

    ## Compute challenge responses
    for idx, j in enumerate(x):
        # si = ri - cxi
        proof.s.append(r[idx] - (proof.c * j))
    return proof


def general_representation_verify(
    y: list[Any],
    g: list[Any],
    i: list[tuple[int, int]],
    prods: list[int],
    proof: GeneralRepresentationProof,
    b_n: str | bytes,
    manual: bool = False,
) -> bool:
    ## Compute the challenge products -- manually until fixing issue23
    prod = []
    if not manual:
        idx = 0
        for j in range(len(y)):
            prod.append(y[j] * proof.c)
            if prods[j] >= 1:
                ## We use prods to specify how the i indexes are 'assigned' per
                ## random 'challenge'
                for k in range(prods[j]):
                    gs = g[i[idx][1]] * proof.s[i[idx][0]]
                    prod[j] = prod[j] + gs
                    idx += 1
    else:
        for idx, j in enumerate(y):
            p = j * proof.c
            if idx == 5:
                idy = idx + 1
            else:
                idy = idx
            gs = g[i[idy][1]] * proof.s[i[idy][0]]
            prod.append(p + gs)
            if idx > 3:
                idy += 1
                gs = g[i[idy][1]] * proof.s[i[idy][0]]
                prod[-1] = prod[-1] + gs
    ## if pi is correct, then pi->c must equal:
    ## Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = y[j]^c*g[i[j,2]]^s[i[j,1]]
    # Push the message
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    # print("bn ver: ", b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    # print(h.hexdigest())
    ## Convert the hash to an integer
    c = Fr.from_hash(h.digest())
    return c == proof.c


def discrete_log_sign(
    G: G1, g: G1, x: Fr, b_n: str | bytes
) -> DiscreteLogProof:
    ## Pick random r and compute g*r mod q
    r = Fr.from_random()
    gr = g * r

    ## Make hc = Hash(msg||G||g||g*r)
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(G.to_bytes())
    h.update(g.to_bytes())
    h.update(gr.to_bytes())

    ## Convert the hash to an integer
    proof = DiscreteLogProof()
    proof.c.set_hash(h.digest())

    # s = r - cx
    proof.s.set_object(r - (proof.c * x))
    return proof


def discrete_log_verify(
    G: G1, g: G1, proof: DiscreteLogProof, b_n: str | bytes
) -> bool:
    ## If pi (proof) is correct, then pi.c must equal Hash(msg||G||g||g*pi.s+g*pi.c)
    ## Compute g*pi.s + g*pi.c
    gsGc = (g * proof.s) + (G * proof.c)

    ## Compute the hash
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(G.to_bytes())
    h.update(g.to_bytes())
    h.update(gsGc.to_bytes())

    ## Compare the result with c
    c = Fr.from_hash(h.digest())
    return c == proof.c


def pairing_homomorphism_sign(
    g: G1, G: GT, xx: G2, b_n: str | bytes
) -> PairingHomomorphismProof:
    ## Pick random R from G2
    rr = G2.from_random()
    ## Compute the map
    R = GT.pairing(g, rr)

    ## Make hc = Hash(msg||g||G||R)
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(g.to_bytes())
    h.update(G.to_bytes())
    h.update(R.to_bytes())

    ## Convert the hash to an integer
    proof = PairingHomomorphismProof()
    proof.c.set_hash(h.digest())

    # s = rr+xx*c
    proof.s.set_object(rr + (xx * proof.c))
    return proof


def pairing_homomorphism_verify(
    g: G1, G: GT, proof: PairingHomomorphismProof, b_n: str | bytes
) -> bool:
    ## If pi is correct, then pi.c equals Hash(msg||g||G||e(g,pi.s)/G**pi.c)
    ## Compute e(g,pi.s)/G**pi.c
    R = GT.pairing(g, proof.s) / (G**proof.c)

    # Compute the hash
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(g.to_bytes())
    h.update(G.to_bytes())
    h.update(R.to_bytes())

    ## Compare the result with c
    c = Fr.from_hash(h.digest())
    return c == proof.c


def pairing_homomorphism_sign2(
    xx: G2, g1: G1, g2: G1, e1: GT, e2: GT, tau: GT, b_n: str | bytes
) -> PairingHomomorphismProof2:
    # RR1 = e(g1,rr), RR2 = e(g2,rr)
    rr = G2.from_random()
    RR1 = GT.pairing(g1, rr)
    RR2 = GT.pairing(g2, rr)

    # c = Hash(g1,g2,e1,e2,RR1,RR2,msg)
    h = hashlib.sha256()
    h.update(g1.to_bytes())
    h.update(g2.to_bytes())
    h.update(e1.to_bytes())
    h.update(e2.to_bytes())
    h.update(RR1.to_bytes())
    h.update(RR2.to_bytes())
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)

    proof = PairingHomomorphismProof2()
    proof.c.set_hash(h.digest())

    # s = rr + xx*c
    proof.s.set_object(rr + (xx * proof.c))
    proof.tau.set_object(tau)
    return proof


def pairing_homomorphism_verify2(
    proof: PairingHomomorphismProof2, g1: G1, g2: G1, e1: GT, b_n: str | bytes
) -> bool:
    # RR1 = e(g1,pi.s)/e1**pi.c
    RR1 = GT.pairing(g1, proof.s) / (e1**proof.c)
    # RR2 = e(g2,pi.s)/e2**pi.c
    RR2 = GT.pairing(g2, proof.s) / (proof.tau**proof.c)
    h = hashlib.sha256()
    h.update(g1.to_bytes())
    h.update(g2.to_bytes())
    h.update(e1.to_bytes())
    h.update(proof.tau.to_bytes())
    h.update(RR1.to_bytes())
    h.update(RR2.to_bytes())
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)

    c = Fr.from_hash(h.digest())
    return c == proof.c
