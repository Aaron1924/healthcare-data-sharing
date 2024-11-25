import hashlib
import logging

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.utils.helpers import (
    GML,
    B64Mixin,
    InfoMixin,
    JoinMixin,
    ReprMixin,
)
from pygroupsig.utils.mcl import G1, G2, GT, Fr

_NAME = "ps16"


class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g = G1()  # Random generator of G1
        self.gg = G2()  # Random generator of G2
        self.X = G2()  # gg^x (x is part of mgrkey)
        self.Y = G2()  # gg^y (y is part of mgrkey)


class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.x = Fr()
        self.y = Fr()


class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.sk = Fr()
        self.sigma1 = G1()
        self.sigma2 = G1()


class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.sigma1 = G1()
        self.sigma2 = G1()
        self.pi = spk.DiscreteLogProof()


class PS16(JoinMixin, ReprMixin, SchemeInterface):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = GML()

    def setup(self):
        ## Set manager key
        self.mgrkey.x.set_random()
        self.mgrkey.y.set_random()

        ## Set group key
        self.grpkey.g.set_random()
        self.grpkey.gg.set_random()
        self.grpkey.X.set_object(self.grpkey.gg * self.mgrkey.x)
        self.grpkey.Y.set_object(self.grpkey.gg * self.mgrkey.y)

    def join_mgr(self, message=None):
        ret = {"status": "error"}
        if message is None:
            ## Send a random element to the member, the member should send it back
            ## to us. This way replay attacks are mitigated
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["phase"] = 1
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
                    tau, self.grpkey.g, proof, n.to_bytes()
                ):
                    e1 = GT.pairing(tau, self.grpkey.Y)
                    e2 = GT.pairing(self.grpkey.g, ttau)

                    if e1 == e2:
                        ## Compute the partial member key
                        u = Fr.from_random()
                        sigma1 = self.grpkey.g * u
                        sigma2 = (
                            (tau * self.mgrkey.y)
                            + (self.grpkey.g * self.mgrkey.x)
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
                    f"Phase not supported for {self.__class__.__name__}"
                )
                self._logger.error(ret["message"])
        return ret

    def join_mem(self, message, key):
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
            key.sk.set_random()
            tau = self.grpkey.g * key.sk
            ttau = self.grpkey.Y * key.sk

            ## Compute the SPK for sk
            proof = spk.discrete_log_sign(
                tau, self.grpkey.g, key.sk, n.to_bytes()
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
            key.sigma1.set_b64(message["sigma1"])
            key.sigma2.set_b64(message["sigma2"])
            ret["status"] = "success"
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            self._logger.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)

        ## Randomize sigma1 and sigma2
        t = Fr.from_random()
        sig = Signature()
        sig.sigma1.set_object(key.sigma1 * t)
        sig.sigma2.set_object(key.sigma2 * t)

        ## Compute signature of knowledge of sk
        # The SPK in PS16 is a dlog spk, but does not follow exactly the
        # pattern of spk_dlog, so we must implement it manually.
        # A good improvement would be to analyze how to generalize spk_dlog
        # to fit this
        k = Fr.from_random()
        e = (GT.pairing(sig.sigma1, self.grpkey.Y)) ** k

        # c = hash(ps16_sig->sigma1,ps16_sig->sigma2,e,m)
        h = hashlib.sha256()
        h.update(sig.sigma1.to_bytes())
        h.update(sig.sigma2.to_bytes())
        h.update(e.to_bytes())
        h.update(message.encode())

        ## Complete the sig
        sig.pi.c.set_hash(h.digest())
        sig.pi.s.set_object(k + (sig.pi.c * key.sk))
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        # e1 = e(-sigma1,X)
        e1 = GT.pairing(-sig.sigma1, self.grpkey.X)
        # e2 = e(sigma2,gg)
        e2 = GT.pairing(sig.sigma2, self.grpkey.gg)
        # e3 = e(sigma1*s,Y)
        e3 = GT.pairing(sig.sigma1 * sig.pi.s, self.grpkey.Y)

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

    def open(self, signature):
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        e1 = GT.pairing(sig.sigma2, self.grpkey.gg)
        e2 = GT.pairing(sig.sigma1, self.grpkey.X)
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

    def open_verify(self, signature, proof):
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        proof_ = spk.PairingHomomorphismProof.from_b64(proof)
        e1 = GT.pairing(sig.sigma2, self.grpkey.gg)
        e2 = GT.pairing(sig.sigma1, self.grpkey.X)
        e4 = e1 / e2
        if spk.pairing_homomorphism_verify(
            sig.sigma1, e4, proof_, sig.to_b64()
        ):
            ret["status"] = "success"
        return ret
