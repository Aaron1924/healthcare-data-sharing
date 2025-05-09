import hashlib
import logging
from typing import Any

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import Container, Scheme
from pygroupsig.utils.helpers import (
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
    _name = "ps16"


class GroupKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataGroupKeyMixin,
    MetadataMixin,
    Container,
):
    g: G1
    gg: G2
    X: G2
    Y: G2

    def __init__(self) -> None:
        self.g = G1()  # Random generator of G1
        self.gg = G2()  # Random generator of G2
        self.X = G2()  # gg^x (x is part of mgrkey)
        self.Y = G2()  # gg^y (y is part of mgrkey)


class ManagerKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataManagerKeyMixin,
    MetadataMixin,
    Container,
):
    x: Fr
    y: Fr

    def __init__(self) -> None:
        self.x = Fr()
        self.y = Fr()


class MemberKey(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataMemberKeyMixin,
    MetadataMixin,
    Container,
):
    sk: Fr
    sigma1: G1
    sigma2: G1

    def __init__(self) -> None:
        self.sk = Fr()
        self.sigma1 = G1()
        self.sigma2 = G1()


class Signature(
    B64Mixin,
    InfoMixin,
    ReprMixin,
    MetadataSignatureMixin,
    MetadataMixin,
    Container,
):
    sigma1: G1
    sigma2: G1
    pi: spk.DiscreteLogProof

    def __init__(self) -> None:
        self.sigma1 = G1()
        self.sigma2 = G1()
        self.pi = spk.DiscreteLogProof()


class Group(
    JoinMixin, ReprMixin, MetadataMixin, Scheme[GroupKey, ManagerKey, MemberKey]
):
    _logger = logging.getLogger(__name__)

    gml: GML

    def __init__(self) -> None:
        self.group_key = GroupKey()
        self.manager_key = ManagerKey()
        self.gml = GML()

    def setup(self) -> None:
        ## Set manager key
        self.manager_key.x.set_random()
        self.manager_key.y.set_random()

        ## Set group key
        self.group_key.g.set_random()
        self.group_key.gg.set_random()
        self.group_key.X.set_object(self.group_key.gg * self.manager_key.x)
        self.group_key.Y.set_object(self.group_key.gg * self.manager_key.y)

    def join_mgr(self, message: dict[str, Any] | None = None) -> dict[str, Any]:
        ret = {"status": "error"}
        if message is None:
            ## Send a random element to the member, the member should send it back
            ## to us. This way replay attacks are mitigated
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["phase"] = 1  # type: ignore
        else:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            phase = message["phase"]
            if phase == 2:
                ## Import the (n,tau,ttau,pi) ad hoc message
                n = G1.from_b64(message["n"])
                tau = G1.from_b64(message["tau"])
                ttau = G2.from_b64(message["ttau"])
                proof = spk.DiscreteLogProof.from_b64(message["pi"])

                if spk.discrete_log_verify(
                    tau, self.group_key.g, proof, n.to_bytes()
                ):
                    e1 = GT.pairing(tau, self.group_key.Y)
                    e2 = GT.pairing(self.group_key.g, ttau)

                    if e1 == e2:
                        ## Compute the partial member key
                        u = Fr.from_random()
                        sigma1 = self.group_key.g * u
                        sigma2 = (
                            (tau * self.manager_key.y)
                            + (self.group_key.g * self.manager_key.x)
                        ) * u

                        ## Add the tuple (i,tau,ttau) to the GML
                        h = hashlib.sha256()
                        h.update(tau.to_bytes())
                        h.update(ttau.to_bytes())
                        self.gml[h.hexdigest()] = (tau, ttau)

                        ## Mout = (sigma1,sigma2)
                        ret["status"] = "success"
                        ret["sigma1"] = sigma1.to_b64()
                        ret["sigma2"] = sigma2.to_b64()
                        ret["phase"] = phase + 1
                    else:
                        ret["status"] = "fail"
                        ret["message"] = "Invalid message content"
                        self._logger.debug("e1 != e2")
                else:
                    ret["status"] = "fail"
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
            ## The manager sends a random element in G1
            n = G1.from_b64(message["n"])

            ## Compute secret exponent, tau and ttau
            member_key.sk.set_random()
            tau = self.group_key.g * member_key.sk
            ttau = self.group_key.Y * member_key.sk

            ## Compute the SPK for sk
            proof = spk.discrete_log_sign(
                tau, self.group_key.g, member_key.sk, n.to_bytes()
            )

            ## Build the output message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["tau"] = tau.to_b64()
            ret["ttau"] = ttau.to_b64()
            ret["pi"] = proof.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            ## Check correctness of computation and update memkey

            # We have sk in memkey, so just need to copy the
            # sigma1 and sigma2 values from the received message,
            # which is an exported (partial) memkey
            member_key.sigma1.set_b64(message["sigma1"])
            member_key.sigma2.set_b64(message["sigma2"])
            ret["status"] = "success"
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}{self._name.upper()}"
            )
            self._logger.error(ret["message"])
        return ret

    def sign(self, message: str, member_key: MemberKey) -> dict[str, Any]:
        message = str(message)

        ## Randomize sigma1 and sigma2
        t = Fr.from_random()
        sig = Signature()
        sig.sigma1.set_object(member_key.sigma1 * t)
        sig.sigma2.set_object(member_key.sigma2 * t)

        ## Compute signature of knowledge of sk
        # The SPK in PS16 is a dlog spk, but does not follow exactly the
        # pattern of spk_dlog, so we must implement it manually.
        # A good improvement would be to analyze how to generalize spk_dlog
        # to fit this
        k = Fr.from_random()
        e = (GT.pairing(sig.sigma1, self.group_key.Y)) ** k

        # c = hash(ps16_sig->sigma1,ps16_sig->sigma2,e,m)
        h = hashlib.sha256()
        h.update(sig.sigma1.to_bytes())
        h.update(sig.sigma2.to_bytes())
        h.update(e.to_bytes())
        h.update(message.encode())

        ## Complete the sig
        sig.pi.c.set_hash(h.digest())
        sig.pi.s.set_object(k + (sig.pi.c * member_key.sk))
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message: str, signature: str) -> dict[str, Any]:
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        # e1 = e(-sigma1,X)
        e1 = GT.pairing(-sig.sigma1, self.group_key.X)
        # e2 = e(sigma2,gg)
        e2 = GT.pairing(sig.sigma2, self.group_key.gg)
        # e3 = e(sigma1*s,Y)
        e3 = GT.pairing(sig.sigma1 * sig.pi.s, self.group_key.Y)

        # R = ((e1*e2)**-c)*e3
        R = ~((e1 * e2) ** sig.pi.c) * e3

        h = hashlib.sha256()
        h.update(sig.sigma1.to_bytes())
        h.update(sig.sigma2.to_bytes())
        h.update(R.to_bytes())
        h.update(message.encode())

        ## Complete the sig
        c = Fr.from_hash(h.digest())

        ## Compare the result with the received challenge
        if c == sig.pi.c:
            ret["status"] = "success"
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("c != sig.pi.c")
        return ret

    def open(self, signature: str) -> dict[str, Any]:
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        e1 = GT.pairing(sig.sigma2, self.group_key.gg)
        e2 = GT.pairing(sig.sigma1, self.group_key.X)
        e4 = e1 / e2
        for mem_id, (_, ttau) in self.gml.items():
            e3 = GT.pairing(sig.sigma1, ttau)
            if e4 == e3:
                ret["status"] = "success"
                ret["id"] = mem_id
                proof = spk.pairing_homomorphism_sign(
                    sig.sigma1, e3, ttau, sig.to_b64()
                )
                ret["proof"] = proof.to_b64()
                break
        return ret

    def open_verify(self, signature: str, proof: str) -> dict[str, Any]:
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        proof_ = spk.PairingHomomorphismProof.from_b64(proof)
        e1 = GT.pairing(sig.sigma2, self.group_key.gg)
        e2 = GT.pairing(sig.sigma1, self.group_key.X)
        e4 = e1 / e2
        if spk.pairing_homomorphism_verify(
            sig.sigma1, e4, proof_, sig.to_b64()
        ):
            ret["status"] = "success"
        return ret
