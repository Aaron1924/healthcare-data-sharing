import hashlib
import logging
from typing import Any

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import Container, Scheme
from pygroupsig.utils.helpers import (
    CRL,
    GML,
    B64Mixin,
    InfoMixin,
    JoinMixin,
    MetadataGroupKeyMixin,
    MetadataManagerKeyMixin,
    MetadataMemberKeyMixin,
    MetadataSignatureMixin,
    ReprMixin,
)
from pygroupsig.utils.mcl import G1, G2, GT, Fr


class MetadataMixin:
    _name = "cpy06"


class GroupKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataGroupKeyMixin,
    MetadataMixin,
    Container,
):
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

    def __init__(self) -> None:
        self.q = G1()  # Q \in_R G1
        self.r = G2()  # R = g2^\gamma; where g2 is G2's generator
        self.w = G2()  # W \in_R G2 \setminus 1
        self.x = G1()  # X = Z^(\xi_1^-1)
        self.y = G1()  # Y = Z^(\xi_2^-1)
        self.z = G1()  # Z \in_R G1 \setminus 1
        # Optimizations
        self.e1 = GT()  # e1 = e(g1, W). Used in sign
        self.e2 = GT()  # e2 = e(z,g2). Used in sign
        self.e3 = GT()  # e3 = e(z,r). Used in sign
        self.e4 = GT()  # e4 = e(g1,g2). Used in sign
        self.e5 = GT()  # e5 = e(q,g2). Used in verify


class ManagerKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataManagerKeyMixin,
    MetadataMixin,
    Container,
):
    xi1: Fr
    xi2: Fr
    gamma: Fr

    def __init__(self) -> None:
        self.xi1 = Fr()  # Exponent for tracing signatures. \xi_1 \in_R Z^*_p
        self.xi2 = Fr()  # Exponent for tracing signatures. \xi_2 \in_R Z^*_p
        # Exponent for generating member keys. \gamma \in_R Z^*_p
        self.gamma = Fr()

class RevocationManagerKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataManagerKeyMixin,
    MetadataMixin,
    Container,
):
    xi1: Fr  # Revocation manager's share of ξ₁
    xi2: Fr  # Revocation manager's share of ξ₂

    def __init__(self) -> None:
        self.xi1 = Fr()  # ξ₁_rev = ξ₁ - ξ₁_group (additive share)
        self.xi2 = Fr()  # ξ₂_rev = ξ₂ - ξ₂_group (additive share)

class MemberKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataMemberKeyMixin,
    MetadataMixin,
    Container,
):
    x: Fr
    t: Fr
    A: G1

    def __init__(self) -> None:
        self.x = Fr()  # x \in_R Z^*_p (non-adaptively chosen by member)
        self.t = Fr()  # t \in_R Z^*_p (chosen by manager)
        self.A = G1()  # A = (q*g_1^x)^(1/t+\gamma)


class Signature(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataSignatureMixin,
    MetadataMixin,
    Container,
):
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

    def __init__(self) -> None:
        self.T1 = G1()
        self.T2 = G1()
        self.T3 = G1()
        self.T4 = G2()
        self.T5 = GT()
        self.c = Fr()
        self.sr1 = Fr()
        self.sr2 = Fr()
        self.sd1 = Fr()
        self.sd2 = Fr()
        self.sx = Fr()
        self.st = Fr()


class Group(
    JoinMixin, ReprMixin, MetadataMixin, Scheme[GroupKey, ManagerKey, MemberKey]
):
    _logger = logging.getLogger(__name__)

    _g1: G1
    _g2: G2
    gml: GML
    crl: CRL

    def __init__(self) -> None:
        self.revocation_manager_key = RevocationManagerKey()
        self.group_key = GroupKey()
        self.manager_key = ManagerKey()
        self._g1 = G1.from_generator()
        self._g2 = G2.from_generator()
        self.gml = GML()
        self.crl = CRL()

    def setup(self) -> None:
        # \xi_1 \in_R Z^*_p
        self.manager_key.xi1.set_random()
        # \xi_2 \in_R Z^*_p
        self.manager_key.xi2.set_random()
        # \gamma \in_R Z^*_p
        self.revocation_manager_key.xi1.set_random()  # ξ₁_rev
        self.revocation_manager_key.xi2.set_random()  # ξ₂_rev
        self.manager_key.gamma.set_random()
        xi1_total = self.manager_key.xi1 + self.revocation_manager_key.xi1
        xi2_total = self.manager_key.xi2 + self.revocation_manager_key.xi2

        ## Create group public key
        # Q \in_R G1
        self.group_key.q.set_random()
        # R = g2^\gamma
        self.group_key.r.set_object(self._g2 * self.manager_key.gamma)
        # W \in_R G2 \setminus 1
        self.group_key.w.set_random()
        # Z \in_R G1 \setminus 1
        while self.group_key.z.is_zero():
            self.group_key.z.set_random()
        # X = Z*(xi_1**-1)
        self.group_key.x.set_object(self.group_key.z * ~xi1_total)
        self.group_key.y.set_object(self.group_key.z * ~xi2_total)
        ## For computation optimizations
        # e1 = e(g1, W)
        self.group_key.e1.set_object(GT.pairing(self._g1, self.group_key.w))
        # e2 = e(z,g2)
        self.group_key.e2.set_object(GT.pairing(self.group_key.z, self._g2))
        # e3 = e(z,r)
        self.group_key.e3.set_object(
            GT.pairing(self.group_key.z, self.group_key.r)
        )
        # e4 = e(g1,g2)
        self.group_key.e4.set_object(GT.pairing(self._g1, self._g2))
        # e5 = e(q,g2)
        self.group_key.e5.set_object(GT.pairing(self.group_key.q, self._g2))

    def join_mgr(self, message: dict[str, Any] | None = None) -> dict[str, Any]:
        ret = {"status": "error"}
        if message is None:
            ## Generate random u, v from Z^*_p
            u = Fr.from_random()
            v = Fr.from_random()

            ## Send u, v, I to member
            ret["status"] = "success"
            ret["u"] = u.to_b64()
            ret["v"] = v.to_b64()
            ret["phase"] = 1  # type: ignore
        else:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            phase = message["phase"]
            if phase == 2:
                ## Input message is <I,pi,spk>
                I_ = G1.from_b64(message["I"])
                pi = G1.from_b64(message["pi"])
                proof = spk.GeneralRepresentationProof.from_b64(message["spk"])
                Y = [pi, pi]
                G = [self._g1, I_, self.group_key.q]
                i = [
                    (0, 0),  # x*g1 (g[0],x[0])
                    (1, 0),  # v*g1 (g[0],x[1])
                    (2, 1),  # u*I (g[1],x[2])
                    (3, 2),  # rr*q (g[2],x[3])
                ]
                prods = [1, 3]

                if spk.general_representation_verify(
                    Y, G, i, prods, proof, pi.to_bytes()
                ):
                    # t \in_R Z^*_p
                    t = Fr.from_random()
                    # A = (pi+q) * ((gamma+t)**-1)
                    A = (pi + self.group_key.q) * ~(self.manager_key.gamma + t)

                    ## Update the gml
                    h = hashlib.sha256()
                    h.update(A.to_bytes())
                    h.update(pi.to_bytes())
                    self.gml[h.hexdigest()] = (A, pi)

                    ## Write the partial memkey into mout
                    ret["status"] = "success"
                    ret["t"] = t.to_b64()
                    ret["A"] = A.to_b64()
                    ret["phase"] = phase + 1
                else:
                    ret["status"] = "fail"
                    ret["message"] = "Invalid message content"
                    self._logger.debug("spk.rep_verify failed")
            else:
                ret["message"] = (
                    f"Phase not supported for {self.__class__.__name__}{self._name.upper()}"
                )
                self._logger.error(ret["message"])
        return ret

    def join_mem(
        self, message: dict[str, Any], member_key: MemberKey
    ) -> dict[str, Any]:
        ret = {"status": "error"}
        if not isinstance(message, dict):
            ret["message"] = "Invalid message type. Expected dict"
            self._logger.error(ret["message"])
            return ret
        phase = message["phase"]
        if phase == 1:
            ## Read u and v from input message
            u = Fr.from_b64(message["u"])
            v = Fr.from_b64(message["v"])

            ## Commit to randomness
            # y,r \in_R Z^*_p
            y = Fr.from_random()
            r = Fr.from_random()

            # I = yG1 + rQ
            e = (G1 * 2)()
            e[0].set_object(self._g1)
            e[1].set_object(self.group_key.q)
            s = (Fr * 2)()
            s[0].set_object(y)
            s[1].set_object(r)
            I_ = G1.muln(e, s)

            ## memkey->x = u*memkey->y + v
            member_key.x.set_object((u * y) + v)

            ## pi = G1*xi
            pi = self._g1 * member_key.x

            ## rr = -r' = -u*r
            rr = -(u * r)

            ## We'll be signing pi in the SPK
            Y = [pi, pi]
            G = [self._g1, I_, self.group_key.q]
            x = [member_key.x, v, u, rr]
            i = [
                (0, 0),  # x*g1 (g[0],x[0])
                (1, 0),  # v*g1 (g[0],x[1])
                (2, 1),  # u*I (g[1],x[2])
                (3, 2),  # rr*q (g[2],x[3])
            ]
            prods = [1, 3]

            proof = spk.general_representation_sign(
                Y, G, x, i, prods, pi.to_bytes()
            )
            ret["status"] = "success"
            ret["I"] = I_.to_b64()
            ret["pi"] = pi.to_b64()
            ret["spk"] = proof.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            ## Import partial key from message
            t_ = Fr.from_b64(message["t"])
            A_ = G1.from_b64(message["A"])
            aux_g2 = (self._g2 * t_) + self.group_key.r
            aux_g1 = (self._g1 * member_key.x) + self.group_key.q

            aux_gt1 = GT.pairing(A_, aux_g2)
            aux_gt2 = GT.pairing(aux_g1, self._g2)
            if aux_gt1 == aux_gt2:
                ## All good: transfer all data to memkey
                member_key.t.set_object(t_)
                member_key.A.set_object(A_)
                ret["status"] = "success"
            else:
                ret["status"] = "fail"
                ret["message"] = "Invalid message content"
                self._logger.debug("aux_gt1 != aux_gt2")
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}{self._name.upper()}"
            )
            self._logger.error(ret["message"])
        return ret

    def sign(self, message: str, member_key: MemberKey) -> dict[str, Any]:
        message = str(message)

        # r1,r2,r3 \in_R Z_p
        r1 = Fr.from_random()
        r2 = Fr.from_random()
        r3 = Fr.from_random()
        # d1 = t*r1
        d1 = member_key.t * r1
        # d2 = t*r2
        d2 = member_key.t * r2

        sig = Signature()
        # T1 = X*r1
        sig.T1.set_object(self.group_key.x * r1)
        # T2 = Y*r2
        sig.T2.set_object(self.group_key.y * r2)
        # T3 = A + Z*(r1+r2)
        sig.T3.set_object(member_key.A + (self.group_key.z * (r1 + r2)))
        # T4 = W*r3
        sig.T4.set_object(self.group_key.w * r3)
        ## e(...) precalculated in setup
        # T5 = e(g1, T4)**x = e(g1, W)**(r3*x)
        sig.T5.set_object(self.group_key.e1 ** (r3 * member_key.x))

        # br1, br2,bd1,bd2,bt,bx \in_R Z_p
        br1 = Fr.from_random()
        br2 = Fr.from_random()
        bd1 = Fr.from_random()
        bd2 = Fr.from_random()
        bt = Fr.from_random()
        bx = Fr.from_random()

        # B1 = X*br1
        B1 = self.group_key.x * br1
        # B2 = Y*br2
        B2 = self.group_key.y * br2
        # B3 = T1*bt - X*bd1
        B3 = (sig.T1 * bt) - (self.group_key.x * bd1)
        # B4 = T2*bt - Y*bd2
        B4 = (sig.T2 * bt) - (self.group_key.y * bd2)
        # B5 = e(g1,T4)^bx
        B5 = GT.pairing(self._g1, sig.T4) ** bx
        # B6 = e(T3,g2)^bt * e(z,g2)^(-bd1-bd2) * e(z,r)^(-br1-br2) * e(g1,g2)^(-bx)
        B6 = GT.pairing(sig.T3, self._g2) ** bt

        ## aux_e: the rest (with the help of the optimizations is easier...)
        e = (GT * 3)()
        e[0].set_object(self.group_key.e2)
        e[1].set_object(self.group_key.e3)
        e[2].set_object(self.group_key.e4)
        s = (Fr * 3)()
        s[0].set_object((-bd1) - bd2)
        s[1].set_object((-br1) - br2)
        s[2].set_object(-bx)
        aux_e = GT.pown(e, s)
        B6 = B6 * aux_e

        # c = hash(M,T1,T2,T3,T4,T5,B1,B2,B3,B4,B5,B6) \in Zp
        h = hashlib.sha256()
        h.update(message.encode())
        h.update(sig.T1.to_bytes())
        h.update(sig.T2.to_bytes())
        h.update(sig.T3.to_bytes())
        h.update(sig.T4.to_bytes())
        h.update(sig.T5.to_bytes())
        h.update(B1.to_bytes())
        h.update(B2.to_bytes())
        h.update(B3.to_bytes())
        h.update(B4.to_bytes())
        h.update(B5.to_bytes())
        h.update(B6.to_bytes())
        sig.c.set_hash(h.digest())

        # sr1 = br1 + c*r1
        sig.sr1.set_object(br1 + (sig.c * r1))
        # sr2 = br2 + c*r2
        sig.sr2.set_object(br2 + (sig.c * r2))
        # sd1 = bd1 + c*d1
        sig.sd1.set_object(bd1 + (sig.c * d1))
        # sd2 = bd2 + c*d2
        sig.sd2.set_object(bd2 + (sig.c * d2))
        # sx = bx + c*x
        sig.sx.set_object(bx + (sig.c * member_key.x))
        # st = bt + c*t
        sig.st.set_object(bt + (sig.c * member_key.t))
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message: str, signature: str) -> dict[str, Any]:
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        ## Re-derive B1, B2, B3, B4, B5 and B6 from the signature
        # B1 = X*sr1 - T1*c
        B1 = (self.group_key.x * sig.sr1) - (sig.T1 * sig.c)
        # B2 = X*sr2 - T2*c
        B2 = (self.group_key.y * sig.sr2) - (sig.T2 * sig.c)
        # B3 = T1*st - X*sd1
        B3 = (sig.T1 * sig.st) - (self.group_key.x * sig.sd1)
        # B4 = T2*st - Y*sd2
        B4 = (sig.T2 * sig.st) - (self.group_key.y * sig.sd2)
        # B5 = e(g1,T4)**sx * T5**-c
        B5 = ((GT.pairing(self._g1, sig.T4)) ** sig.sx) * ~(sig.T5**sig.c)
        # B6 = e(T3,g2)^st * e(z,g2)^(-sd1-sd2) * e(z,r)^(-sr1-sr2) * e(g1,g2)^(-sx) * ( e(T3,r)/e(q,g2) )^c
        # aux_e = e(z,g2)^(-sd1-sd2) * e(z,r)^(-sr1-sr2) * e(g1,g2)^(-sx)
        e = (GT * 3)()
        e[0].set_object(self.group_key.e2)
        e[1].set_object(self.group_key.e3)
        e[2].set_object(self.group_key.e4)
        s = (Fr * 3)()
        s[0].set_object((-sig.sd1) - sig.sd2)
        s[1].set_object((-sig.sr1) - sig.sr2)
        s[2].set_object(-sig.sx)
        aux_e = GT.pown(e, s)

        # aux_GT = (e(T3,r) / e(q,g2))**c
        aux_GT = (
            (GT.pairing(sig.T3, self.group_key.r)) / self.group_key.e5
        ) ** sig.c

        # B6 = e(T3,g2)^st * aux_e * aux_GT
        B6 = (GT.pairing(sig.T3, self._g2)) ** sig.st * aux_e * aux_GT

        ## Recompute the hash-challenge c
        h = hashlib.sha256()
        h.update(message.encode())
        h.update(sig.T1.to_bytes())
        h.update(sig.T2.to_bytes())
        h.update(sig.T3.to_bytes())
        h.update(sig.T4.to_bytes())
        h.update(sig.T5.to_bytes())
        h.update(B1.to_bytes())
        h.update(B2.to_bytes())
        h.update(B3.to_bytes())
        h.update(B4.to_bytes())
        h.update(B5.to_bytes())
        h.update(B6.to_bytes())
        c = Fr.from_hash(h.digest())

        ## Compare the result with the received challenge
        if c == sig.c:
            ret["status"] = "success"
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("c != sig.c")
        return ret

    def open(self, signature: str,group_manager_partial: dict[str, Any] = None, revocation_manager_partial: dict[str, Any] = None) -> dict[str, Any]:
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        ## Recover the signer's A as: A = T3-(T1*xi1 + T2*xi2)
        # A = T1*xi1 + T2*xi2 =
        if group_manager_partial is None:
        # Group Manager computes partial decryption
            partial_g = {
                "T1_xi": self.manager_key.xi1,
                "T2_xi": self.manager_key.xi2
            }
            return {"status": "partial", "partial_g": partial_g}
        elif revocation_manager_partial is None:
        # Revocation Manager computes partial decryption
            partial_r = {
                "T1_xi": self.revocation_manager_key.xi1,
                "T2_xi": self.revocation_manager_key.xi2
            }
            return {"status": "partial", "partial_r": partial_r}
        else:
            xi1_total = group_manager_partial["T1_xi"] + revocation_manager_partial["T1_xi"]
            xi2_total = group_manager_partial["T2_xi"] + revocation_manager_partial["T2_xi"]

            e = (G1 * 2)()
            e[0].set_object(sig.T1)
            e[1].set_object(sig.T2)
            s = (Fr * 2)()
            s[0].set_object(xi1_total)
            s[1].set_object(xi2_total)
            A = G1.muln(e, s)
            A = sig.T3 - A

        # Lookup A in GML
            for mem_id, (open_trap, _) in self.gml.items():
                if A == open_trap:
                    return {"status": "success", "id": mem_id}
            return {"status": "fail"}
            

    def reveal(self, member_id: str) -> dict[str, Any]:
        ret = {"status": "fail"}
        if member_id in self.gml:
            ret["status"] = "success"
            self.crl[member_id] = self.gml[member_id]
        return ret

    def trace(self, signature: str) -> dict[str, Any]:
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        for _, (_, trace_trap) in self.crl.items():
            e = GT.pairing(trace_trap, sig.T4)
            if e == sig.T5:
                ret["status"] = "success"
                ret["revoked"] = True  # type: ignore
                break
        return ret

    def prove_equality(
        self, signatures: list[str], member_key: MemberKey
    ) -> dict[str, Any]:
        ## Initialize the hashing environment
        h = hashlib.sha256()
        ## Get random r
        r = Fr.from_random()
        ## To create the proof, we make use of the T4 and T5 objects of the signatures.
        ## The knowledge of the discrete logarithm of T5 to the base e(g1,T4) is used in
        ## normal signature claims. In the same way, given two signatures (allegedly)
        ## issued by the same member, with corresponding objects T4, T5, T4' and T5', we
        ## prove here that the discrete logarithm of T5 to the base e(g1,T4) is the same
        ## to that of T5' to the base e(g1,T4')

        ## (1) Raise e(g1,T4) of each received signature to r, and put it into the hash
        for s in signatures:
            sig = Signature.from_b64(s)
            e = GT.pairing(self._g1, sig.T4)
            er = e**r
            ## Put the i-th e(g1,T4)^r element of the array
            h.update(er.to_bytes())
            ## Put the also the base ( = e(g1,T4) ) into the hash
            h.update(e.to_bytes())
            ## ... and T5
            h.update(sig.T5.to_bytes())

        proof = spk.NizkProof()
        ## (2) Calculate c = hash((e(g1,T4)^r)[1] || (e(g1,T4))[1] || ... ||
            ## (e(g1,T4)^r)[n] || (e(g1,T4))[n] )
        proof.c.set_hash(h.digest())
        ## (3) To end, get s = r - c*x
        proof.s.set_object(r + (proof.c * member_key.x))
        return {
            "status": "success",
            "proof": proof.to_b64(),
        }

    def prove_equality_verify(
        self, signatures: list[str], proof: str
    ) -> dict[str, Any]:
        ret = {"status": "fail"}
        ## Initialize the hashing environment
        h = hashlib.sha256()
        ## We have to recover the e(g1,T4)^r objects. To do so,
        ## we divide e(g1,T4)^s/T5^c
        proof_ = spk.NizkProof.from_b64(proof)
        for s in signatures:
            sig = Signature.from_b64(s)
            e = GT.pairing(self._g1, sig.T4)
            es = (e**proof_.s) / (sig.T5**proof_.c)
            ## Put the i-th element of the array
            h.update(es.to_bytes())
            ## Put also the base (the e(g1,T4)'s) into the hash
            h.update(e.to_bytes())
            ## ... and T5
            h.update(sig.T5.to_bytes())

        ## (2) Calculate c = hash((e(g1,T4)^r)[1] || (e(g1,T4))[1] || ... ||
        ## (e(g1,T4)^r)[n] || (e(g1,T4))[n] )
        ## Now, we have to get c as an element
        c = Fr.from_hash(h.digest())
        if c == proof_.c:
            ret["status"] = "success"
        else:
            ret["message"] = "Invalid proof"
            self._logger.debug("c != proof_.c")
        return ret

    def claim(self, signature: str, member_key: MemberKey) -> dict[str, Any]:
        ## A claim is just similar to proving "equality" of N sigature, but just
        ## for 1 signature
        return self.prove_equality([signature], member_key)

    def claim_verify(self, signature: str, proof: str) -> dict[str, Any]:
        ## A claim verification is just similar to proving "equality verification" of N sigature, but just
        ## for 1 signature
        return self.prove_equality_verify([signature], proof)
