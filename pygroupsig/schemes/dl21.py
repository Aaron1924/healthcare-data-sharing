import hashlib
import logging
from typing import Any, Generic, Type, TypeVar

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import Container, Scheme
from pygroupsig.utils.helpers import (
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
    _name = "dl21"


class GroupKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataGroupKeyMixin,
    MetadataMixin,
    Container,
):
    g1: G1
    g2: G2
    h1: G1
    h2: G1
    ipk: G2

    def __init__(self) -> None:
        self.g1 = G1()  # Params. Random generator of G1
        self.g2 = G2()  # Params. Random generator of G2
        self.h1 = G1()  # Params. Random generator of G1
        self.h2 = G1()  # Params. Random generator of G1
        self.ipk = G2()  # Isseur public key


class ManagerKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataManagerKeyMixin,
    MetadataMixin,
    Container,
):
    isk: Fr

    def __init__(self) -> None:
        self.isk = Fr()  # Issuer secret key


class MemberKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataMemberKeyMixin,
    MetadataMixin,
    Container,
):
    A: G1
    x: Fr
    y: Fr
    s: Fr
    H: G1
    h2s: G1

    def __init__(self) -> None:
        self.A = G1()  # A = (H*h2^s*g1)^(1/isk+x)
        self.x = Fr()  # Randomly picked by the Issuer
        self.y = Fr()  # Randomly picked by the Member
        self.s = Fr()  # Randomly picked by the Issuer
        self.H = G1()  # Member's "public key". H = h1^y
        self.h2s = G1()  # Used in signatures. h2s = h2^s


class Signature(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataSignatureMixin,
    MetadataMixin,
    Container,
):
    AA: G1
    A_: G1
    d: G1
    pi: spk.GeneralRepresentationProof
    nym: G1

    def __init__(self) -> None:
        self.AA = G1()
        self.A_ = G1()
        self.d = G1()
        self.pi = spk.GeneralRepresentationProof()
        self.nym = G1()


SignatureT = TypeVar("SignatureT", bound=Signature)


class Group(
    JoinMixin,
    ReprMixin,
    MetadataMixin,
    Generic[SignatureT],
    Scheme[GroupKey, ManagerKey, MemberKey],
):
    _logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.group_key = GroupKey()
        self.manager_key = ManagerKey()

    def setup(self) -> None:
        ## Initialize the manager key
        self.manager_key.isk.set_random()

        ## Initialize the group key
        self.group_key.g1.set_random()
        self.group_key.h1.set_random()
        self.group_key.h2.set_random()

        ## Compute random generator g2 in G2. Since G2 is a cyclic group of prime
        ## order, just pick a random element
        self.group_key.g2.set_random()

        ## Set the Issuer public key
        self.group_key.ipk.set_object(self.group_key.g2 * self.manager_key.isk)

    def join_mgr(self, message: dict[str, Any] | None = None) -> dict[str, Any]:
        ret = {"status": "error"}
        if message is None:
            ## Send a random element to the member
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["phase"] = 1  # type: ignore
            ## TODO: This value should be saved in some place to avoid replay attack
        else:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            phase = message["phase"]
            if phase == 2:
                ## Second step by manager: compute credential from H and pi_H */
                ## Verify the proof
                n = G1.from_b64(message["n"])
                H = G1.from_b64(message["H"])
                proof = spk.DiscreteLogProof.from_b64(message["pi"])
                if spk.discrete_log_verify(
                    H, self.group_key.h1, proof, n.to_bytes()
                ):
                    ## Pick x and s at random from Z*_p
                    x = Fr.from_random()
                    s = Fr.from_random()

                    # Set A = (H+h_2*s+g_1)*((isk+x)**-1)
                    A = (H + (self.group_key.h2 * s) + self.group_key.g1) * ~(
                        self.manager_key.isk + x
                    )

                    ## Mout = (A,x,s)
                    ## This is stored in a partially filled memkey, byte encoded into a
                    ## message_t struct
                    ret["status"] = "success"
                    ret["x"] = x.to_b64()
                    ret["s"] = s.to_b64()
                    ret["A"] = A.to_b64()
                    ret["phase"] = phase + 1
                else:
                    ret["message"] = "Invalid message content"
                    self._logger.debug("spk.dlog_G1_verify failed")
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
            ## First step by the member: parse n and compute (Y,\pi_Y)
            n = G1.from_b64(message["n"])

            ## Compute member's secret key y at random
            member_key.y.set_random()

            ## Compute the member's public key
            member_key.H.set_object(self.group_key.h1 * member_key.y)

            ## Compute the SPK
            proof = spk.discrete_log_sign(
                member_key.H, self.group_key.h1, member_key.y, n.to_bytes()
            )

            ## Build the output message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["H"] = member_key.H.to_b64()
            ret["pi"] = proof.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            ## Second step by the member: Check correctness of computation
            ## and update memkey
            member_key.x.set_b64(message["x"])
            member_key.s.set_b64(message["s"])
            member_key.A.set_b64(message["A"])

            ## Recompute h2s from s
            member_key.h2s.set_object(self.group_key.h2 * member_key.s)

            ## Check correctness

            ## A must not be 1 (since we use additive notation for G1,
            ## it must not be 0)
            if not member_key.A.is_zero():
                # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
                e1 = (
                    GT.pairing(member_key.A, self.group_key.g2)
                ) ** member_key.x
                e2 = GT.pairing(member_key.A, self.group_key.ipk)
                e4 = e1 * e2
                aux = (member_key.h2s + member_key.H) + self.group_key.g1
                e3 = GT.pairing(aux, self.group_key.g2)
                if e4 == e3:
                    ret["status"] = "success"
                else:
                    ret["status"] = "fail"
                    ret["message"] = "Invalid message content"
                    self._logger.debug("e4 != e3")
            else:
                ret["status"] = "fail"
                ret["message"] = "Invalid message content"
                self._logger.debug("key.A is zero")
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}{self._name.upper()}"
            )
            self._logger.error(ret["message"])
        return ret

    _scheme_signature: Type[SignatureT] = Signature  # type: ignore

    def sign(
        self, message: str, member_key: MemberKey, scope: str = "def"
    ) -> dict[str, Any]:
        sig = self._common_sign(message, member_key, scope)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def _common_sign(
        self, message: str, member_key: MemberKey, scope: str
    ) -> SignatureT:
        message = str(message)
        scope = str(scope)
        # r1, r2 \in_R Z_p
        r1 = Fr.from_random()
        r2 = Fr.from_random()

        sig = self._scheme_signature()
        # nym = Hash(scp)*y
        h = hashlib.sha256(scope.encode())
        hscp = G1.from_hash(h.digest())
        sig.nym.set_object(hscp * member_key.y)

        # AA = A*r1
        sig.AA.set_object(member_key.A * r1)

        ## Good thing we precomputed much of this...
        # aux = (g1*h1^y*h2^s)^r1
        aux = (self.group_key.g1 + member_key.H + member_key.h2s) * r1
        # A_ = AA*-x+(g1+h1*y+h2*s)*r1
        sig.A_.set_object((sig.AA * -member_key.x) + aux)

        # d = (g1+h1*y+h2*s)*r1+h2*-r2
        sig.d.set_object(aux + (self.group_key.h2 * -r2))

        # r3 = r1**-1
        r3 = ~r1

        # ss = s - r2*r3
        ss = member_key.s - (r2 * r3)
        ## Auxiliar variables for the spk
        aux_Zr = -member_key.x
        ss = -ss
        negy = -member_key.y
        A_d = sig.A_ - sig.d

        y = [sig.nym, A_d, self.group_key.g1]
        g = [hscp, sig.AA, self.group_key.h2, sig.d, self.group_key.h1]
        x = [aux_Zr, member_key.y, r2, r3, ss, negy]
        i = [
            (1, 0),  # hscp^y = (g[0],x[1])
            (0, 1),  # AA^-x = (g[1],x[0])
            (2, 2),  # h2^r2 = (g[2],x[2])
            (3, 3),  # d^r3 = (g[3],x[3])
            (4, 2),  # h2^-ss = (g[2],x[4])
            (5, 4),  # h1^-y = (g[4],x[5])
        ]
        prods = [1, 2, 3]
        proof = spk.general_representation_sign(y, g, x, i, prods, message)
        sig.pi.c.set_object(proof.c)
        sig.pi.s.extend(proof.s)
        return sig

    def verify(
        self, message: str, signature: str, scope: str = "def"
    ) -> dict[str, Any]:
        message = str(message)
        scope = str(scope)
        ret = {"status": "fail"}
        sig = self._scheme_signature.from_b64(signature)
        ## AA must not be 1 (since we use additive notation for G1,
        ## it must not be 0)
        if not sig.AA.is_zero():
            ## e(AA,ipk) must equal e(A_,g2)
            e1 = GT.pairing(sig.AA, self.group_key.ipk)
            e2 = GT.pairing(sig.A_, self.group_key.g2)
            if e1 == e2:
                ## Recompute hscp
                h = hashlib.sha256(scope.encode())
                hscp = G1.from_hash(h.digest())
                A_d = sig.A_ - sig.d
                y = [sig.nym, A_d, self.group_key.g1]
                g = [hscp, sig.AA, self.group_key.h2, sig.d, self.group_key.h1]
                i = [
                    (1, 0),  # hscp^y = (g[0],x[1])
                    (0, 1),  # AA^-x = (g[1],x[0])
                    (2, 2),  # h2^r2 = (g[2],x[2])
                    (3, 3),  # d^r3 = (g[3],x[3])
                    (4, 2),  # h2^-ss = (g[2],x[4])
                    (5, 4),  # h1^-y = (g[4],x[5])
                ]
                prods = [1, 2, 3]
                ## Verify SPK
                if spk.general_representation_verify(
                    y, g, i, prods, sig.pi, message
                ):
                    ret["status"] = "success"
                else:
                    ret["message"] = "Invalid signature"
                    self._logger.debug("spk.rep_verify failed")
            else:
                ret["message"] = "Invalid signature"
                self._logger.debug("e1 != e2")
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("AA is zero")
        return ret

    # noinspection PyUnresolvedReferences
    def identify(
        self, signature: str, member_key: MemberKey, scope: str = "def"
    ) -> dict[str, Any]:
        scope = str(scope)
        ret = {"status": "fail"}
        sig = self._scheme_signature.from_b64(signature)
        ## Recompute nym
        h = hashlib.sha256()
        h.update(scope.encode())
        hscp = G1.from_hash(h.digest())
        nym = hscp * member_key.y
        ## Check if nym = h(scp)*y
        if nym == sig.nym:
            ret["status"] = "success"
        return ret

    def link(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        member_key: MemberKey,
        scope: str = "def",
    ) -> dict[str, Any]:
        scope = str(scope)
        ret = {"status": "fail"}
        hscp = G1()
        for msg, sig_b64 in zip(messages, signatures):
            ## Verify signature
            ver_msg = self.verify(msg, sig_b64, scope=scope)
            ## Check if it is a signature issued by memkey
            iden_msg = self.identify(sig_b64, member_key, scope=scope)
            h = hashlib.sha256()
            if (
                ver_msg["status"] == "success"
                and iden_msg["status"] == "success"
            ):
                h.update(scope.encode())
                ## "Accumulate" scp
                hscp += G1.from_hash(h.digest())
            else:
                if ver_msg["status"] != "success":
                    ret["message1"] = "Invalid messages/signatures"
                    self._logger.debug("Signature verify failed")
                if iden_msg["status"] != "success":
                    ret["message2"] = "Invalid messages/signatures"
                    self._logger.debug("Signature identify failed")
                break
        else:
            # nym_ = hscp * y
            nym = hscp * member_key.y
            ## Do the SPK
            proof = spk.discrete_log_sign(nym, hscp, member_key.y, message)
            ret["status"] = "success"
            ret["proof"] = proof.to_b64()
        return ret

    # noinspection PyUnresolvedReferences
    def link_verify(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        proof: str,
        scope: str = "def",
    ) -> dict[str, Any]:
        scope = str(scope)
        ret = {"status": "fail"}
        proof_ = spk.DiscreteLogProof.from_b64(proof)
        hscp = G1()
        nym = G1()
        for msg, sig_b64 in zip(messages, signatures):
            ver_msg = self.verify(msg, sig_b64)
            if ver_msg["status"] == "success":
                h = hashlib.sha256()
                h.update(scope.encode())
                ## "Accumulate" scp
                hscp += G1.from_hash(h.digest())
                ## "Accumulate" nym
                sig = self._scheme_signature.from_b64(sig_b64)
                nym += sig.nym
            else:
                ret["message"] = "Invalid messages/signatures"
                self._logger.debug("Signature verify failed")
                break
        else:
            if spk.discrete_log_verify(nym, hscp, proof_, message):
                ret["status"] = "success"
            else:
                ret["message"] = "Invalid proof"
                self._logger.debug("spk.dlog_G1_verify failed")
        return ret
