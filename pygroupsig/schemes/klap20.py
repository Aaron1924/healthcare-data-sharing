import hashlib
import logging
import random

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

_NAME = "klap20"


class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g = G1()  # Random generator of G1
        self.gg = G2()  # Random generator of G1
        self.XX = G2()  # gg^x (x is part of mgrkey)
        self.YY = G2()  # gg^y (y is part of mgrkey)
        self.ZZ0 = G2()  # gg^z0 (z0 is part of mgrkey)
        self.ZZ1 = G2()  # gg^z1 (z1 is part of mgrkey)


class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.x = Fr()  # Issuer component x
        self.y = Fr()  # Issuer component y
        self.z0 = Fr()  # Opener component z_0
        self.z1 = Fr()  # Opener component z_1


class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.alpha = Fr()
        self.u = G1()
        self.v = G1()
        self.w = G1()


class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.uu = G1()
        self.vv = G1()
        self.ww = G1()
        self.pi = spk.DiscreteLogProof()


class KLAP20(JoinMixin, ReprMixin, SchemeInterface):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = GML()

    def setup(self):
        ## Initializes the Issuer's key
        self.mgrkey.x.set_random()
        self.mgrkey.y.set_random()

        ## Initializes the Group key
        # Compute random generators g and gg. Since G1 and G2 are cyclic
        # groups of prime order, just pick random elements
        self.grpkey.g.set_random()
        self.grpkey.gg.set_random()

        ## Partially fill the group key with the Issuer's public key
        self.grpkey.XX.set_object(self.grpkey.gg * self.mgrkey.x)
        self.grpkey.YY.set_object(self.grpkey.gg * self.mgrkey.y)

        ## Initialize the Opener's key
        self.mgrkey.z0.set_random()
        self.mgrkey.z1.set_random()

        ## Finalize the group key with the Opener's public key
        self.grpkey.ZZ0.set_object(self.grpkey.gg * self.mgrkey.z0)
        self.grpkey.ZZ1.set_object(self.grpkey.gg * self.mgrkey.z1)

    def join_mgr(self, message=None):
        ret = {"status": "error"}
        if message is None:
            ## Send a random element to the member
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["phase"] = 1
            ## TODO: This value should be saved in some place to avoid replay attack
        else:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            phase = message["phase"]
            if phase == 2:
                ## Import the (n,f,w,SSO,SS1,ff0,ff1,pi) ad hoc message
                n = G1.from_b64(message["n"])
                f = G1.from_b64(message["f"])
                w = G1.from_b64(message["w"])
                SS0 = G2.from_b64(message["SS0"])
                SS1 = G2.from_b64(message["SS1"])
                ff0 = G2.from_b64(message["ff0"])
                ff1 = G2.from_b64(message["ff1"])
                proof = spk.GeneralRepresentationProof.from_b64(message["pi"])
                ## Check the SPK -- this will change with issue23
                ## Compute the SPK for sk -- this will be replaced in issue23
                # u = Hash(f)
                h = hashlib.sha256(f.to_bytes())
                u = G1.from_hash(h.digest())

                y = [f, w, SS0, SS1, ff0, ff1]
                g = [
                    self.grpkey.g,
                    u,
                    self.grpkey.gg,
                    self.grpkey.ZZ0,
                    self.grpkey.ZZ1,
                ]
                i = [
                    (0, 0),  # alpha, g
                    (0, 1),  # alpha, u
                    (1, 2),  # s0, gg
                    (2, 2),  # s1, gg
                    (0, 2),  # alpha, gg
                    (1, 3),  # s0, ZZ0
                    (0, 2),  # alpha, gg
                    (2, 4),
                ]  # s1, ZZ1
                prods = [1, 1, 1, 1, 2, 2]
                if spk.general_representation_verify(
                    y, g, i, prods, proof, n.to_bytes(), manual=True
                ):
                    v = (u * self.mgrkey.x) + (w * self.mgrkey.y)
                    # Add the tuple (i,SS0,SS1,ff0,ff1,tau) to the GML
                    tau = GT.pairing(f, self.grpkey.gg)
                    # Currently, KLAP20 identities are just uint64_t's
                    h = hashlib.sha256()
                    h.update(SS0.to_bytes())
                    h.update(SS1.to_bytes())
                    h.update(ff0.to_bytes())
                    h.update(ff1.to_bytes())
                    h.update(tau.to_bytes())

                    self.gml[h.hexdigest()] = (SS0, SS1, ff0, ff1, tau)

                    ret["status"] = "success"
                    ret["v"] = v.to_b64()
                    ret["phase"] = phase + 1
                else:
                    ret["status"] = "fail"
                    ret["message"] = "Invalid message content"
                    self._logger.debug("spk.verify failed")
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

            ## Compute secret alpha, s0 and s1
            key.alpha.set_random()

            s0 = Fr.from_random()
            s1 = Fr.from_random()

            # f = g*alpha
            f = self.grpkey.g * key.alpha
            # u = Hash(f)
            h = hashlib.sha256(f.to_bytes())
            key.u.set_hash(h.digest())

            # w = u*alpha
            key.w.set_object(key.u * key.alpha)

            # SS0 = gg*s0
            SS0 = self.grpkey.gg * s0
            # SS1 = gg*s1
            SS1 = self.grpkey.gg * s1

            ggalpha = self.grpkey.gg * key.alpha
            # ff0 = gg*alpha+ZZ0*s0
            ff0 = ggalpha + (self.grpkey.ZZ0 * s0)
            # ff1 = gg*alpha+ZZ1*s1
            ff1 = ggalpha + (self.grpkey.ZZ1 * s1)

            # tau = e(f,gg)
            # tau = GT.pairing(f, self.grpkey.gg)
            ## TODO: Whats the usage of tau in this current phase?

            y = [f, key.w, SS0, SS1, ff0, ff1]
            g = [
                self.grpkey.g,
                key.u,
                self.grpkey.gg,
                self.grpkey.ZZ0,
                self.grpkey.ZZ1,
            ]
            x = [key.alpha, s0, s1]
            i = [
                (0, 0),  # alpha, g
                (0, 1),  # alpha, u
                (1, 2),  # s0, gg
                (2, 2),  # s1, gg
                (0, 2),  # alpha, gg
                (1, 3),  # s0, ZZ0
                (0, 2),  # alpha, gg
                (2, 4),  # s1, ZZ1
            ]
            prods = [1, 1, 1, 1, 2, 2]
            proof = spk.general_representation_sign(
                y, g, x, i, prods, n.to_bytes(), manual=True
            )
            ## Need to send (n, f, w, SS0, SS1, ff0, ff1, pi): prepare ad hoc message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["f"] = f.to_b64()
            ret["w"] = key.w.to_b64()
            ret["SS0"] = SS0.to_b64()
            ret["SS1"] = SS1.to_b64()
            ret["ff0"] = ff0.to_b64()
            ret["ff1"] = ff1.to_b64()
            ret["pi"] = proof.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                self._logger.error(ret["message"])
                return ret
            # Min = v
            key.v = G1.from_b64(message["v"])
            # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
            e1 = GT.pairing(key.v, self.grpkey.gg)
            e2 = GT.pairing(key.u, self.grpkey.XX)
            e3 = GT.pairing(key.w, self.grpkey.YY)
            e4 = e2 * e3
            if e1 == e4:
                ret["status"] = "success"
            else:
                ret["status"] = "fail"
                ret["message"] = "Invalid message content"
                self._logger.debug("e1 != e4")
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            self._logger.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)
        ## Randomize u, v and w
        r = Fr.from_random()
        sig = Signature()
        sig.uu.set_object(key.u * r)
        sig.vv.set_object(key.v * r)
        sig.ww.set_object(key.w * r)

        ## Compute signature of knowledge of alpha
        proof = spk.discrete_log_sign(sig.ww, sig.uu, key.alpha, message)
        sig.pi.c.set_object(proof.c)
        sig.pi.s.set_object(proof.s)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        ## Verify SPK
        if spk.discrete_log_verify(sig.ww, sig.uu, sig.pi, message):
            # e1 = e(vv,gg)
            e1 = GT.pairing(sig.vv, self.grpkey.gg)
            # e2 = e(uu,XX)
            e2 = GT.pairing(sig.uu, self.grpkey.XX)
            # e3 = e(ww,YY)
            e3 = GT.pairing(sig.ww, self.grpkey.YY)
            e4 = e2 * e3
            ## Compare the result with the received challenge
            if e1 == e4:
                ret["status"] = "success"
            else:
                ret["message"] = "Invalid signature"
                self._logger.debug("e1 != e4")
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("spk.dlog_G1_verify failed")
        return ret

    def open(self, signature):
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        b = random.randint(0, 1)
        for mem_id, (SS0, SS1, ff0, ff1, tau) in self.gml.items():
            if b:
                aux = -(SS1 * self.mgrkey.z1)
                ff = ff1 + aux
            else:
                aux = -(SS0 * self.mgrkey.z0)
                ff = ff0 + aux
            e1 = GT.pairing(sig.uu, ff)
            e2 = GT.pairing(sig.ww, self.grpkey.gg)
            e3 = GT.pairing(self.grpkey.g, ff)
            if e1 == e2 and tau == e3:
                ret["status"] = "success"
                ret["id"] = mem_id
                proof = spk.pairing_homomorphism_sign2(
                    ff, sig.uu, self.grpkey.g, e2, e3, tau, sig.to_b64()
                )
                ret["proof"] = proof.to_b64()
                break
        return ret

    def open_verify(self, signature, proof):
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        proof_ = spk.PairingHomomorphismProof2.from_b64(proof)
        e2 = GT.pairing(sig.ww, self.grpkey.gg)
        if spk.pairing_homomorphism_verify2(
            proof_, sig.uu, self.grpkey.g, e2, sig.to_b64()
        ):
            ret["status"] = "success"
        return ret
