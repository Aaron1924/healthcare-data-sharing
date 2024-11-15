import hashlib
import logging

import pygroupsig.spk as spk
from pygroupsig.helpers import B64Mixin, InfoMixin, ReprMixin
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.pairings.mcl import G1, G2, GT, Fr

_NAME = "dl21"
_SEQ = 3
_START = 0

logger = logging.getLogger(__name__)


class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g1 = G1()  # Params. Random generator of G1
        self.g2 = G2()  # Params. Random generator of G2
        self.h1 = G1()  # Params. Random generator of G1
        self.h2 = G1()  # Params. Random generator of G1
        self.ipk = G2()  # Isseur public key


class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.isk = Fr()  # Issuer secret key


class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.A = G1()  # A = (H*h2^s*g1)^(1/isk+x)
        self.x = Fr()  # Randomly picked by the Issuer
        self.y = Fr()  # Randomly picked by the Member
        self.s = Fr()  # Randomly picked by the Issuer
        self.H = G1()  # Member's "public key". H = h1^y
        self.h2s = G1()  # Used in signatures. h2s = h2^s


class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.AA = G1()
        self.A_ = G1()
        self.d = G1()
        self.c = Fr()
        self.s = []
        self.nym = G1()


class DL21(ReprMixin, SchemeInterface):
    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()

    def setup(self):
        ## Initialize the manager key
        self.mgrkey.isk.set_random()

        ## Initialize the group key
        self.grpkey.g1.set_random()
        self.grpkey.h1.set_random()
        self.grpkey.h2.set_random()

        ## Compute random generator g2 in G2. Since G2 is a cyclic group of prime
        ## order, just pick a random element
        self.grpkey.g2.set_random()

        ## Set the Issuer public key
        self.grpkey.ipk.set_object(self.grpkey.g2 * self.mgrkey.isk)

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
                logger.error(ret["message"])
                return ret
            phase = message["phase"]
            if phase == 2:
                ## Second step by manager: compute credential from H and pi_H */
                ## Verify the proof
                n = G1.from_b64(message["n"])
                H = G1.from_b64(message["H"])
                pic = Fr.from_b64(message["pic"])
                pis = Fr.from_b64(message["pis"])
                if spk.dlog_G1_verify(
                    H, self.grpkey.h1, pic, pis, n.to_bytes()
                ):
                    ## Pick x and s at random from Z*_p
                    x = Fr.from_random()
                    s = Fr.from_random()

                    # Set A = (H+h_2*s+g_1)*((isk+x)**-1)
                    A = (H + (self.grpkey.h2 * s) + self.grpkey.g1) * ~(
                        self.mgrkey.isk + x
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
                    ret["message"] = "spk.dlog_G1_verify failed"
                    logger.error(ret["message"])
            else:
                ret["message"] = (
                    f"Phase not supported for {self.__class__.__name__}"
                )
                logger.error(ret["message"])
        return ret

    def join_mem(self, message, key):
        ret = {"status": "error"}
        if not isinstance(message, dict):
            ret["message"] = "Invalid message type. Expected dict"
            logger.error(ret["message"])
            return ret
        phase = message["phase"]
        if phase == 1:
            ## First step by the member: parse n and compute (Y,\pi_Y)
            n = G1.from_b64(message["n"])

            ## Compute member's secret key y at random
            key.y.set_random()

            ## Compute the member's public key
            key.H.set_object(self.grpkey.h1 * key.y)

            ## Compute the SPK
            pic, pis = spk.dlog_G1_sign(
                key.H, self.grpkey.h1, key.y, n.to_bytes()
            )

            ## Build the output message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["H"] = key.H.to_b64()
            ret["pic"] = pic.to_b64()
            ret["pis"] = pis.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            ## Second step by the member: Check correctness of computation
            ## and update memkey
            key.x.set_b64(message["x"])
            key.s.set_b64(message["s"])
            key.A.set_b64(message["A"])

            ## Recompute h2s from s
            key.h2s.set_object(self.grpkey.h2 * key.s)

            ## Check correctness

            ## A must not be 1 (since we use additive notation for G1,
            ## it must not be 0)
            if not key.A.is_zero():
                # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
                e1 = (GT.pairing(key.A, self.grpkey.g2)) ** key.x
                e2 = GT.pairing(key.A, self.grpkey.ipk)
                e4 = e1 * e2
                aux = (key.h2s + key.H) + self.grpkey.g1
                e3 = GT.pairing(aux, self.grpkey.g2)
                if e4 == e3:
                    ret["status"] = "success"
                else:
                    ret["status"] = "fail"
                    ret["message"] = "e4 != e3"
                    logger.error(ret["message"])
            else:
                ret["status"] = "fail"
                ret["message"] = "key.A is zero"
                logger.error(ret["message"])
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logger.error(ret["message"])
        return ret

    def sign(self, message, key, scope="def"):
        sig = self._common_sign(message, key, scope)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def _common_sign(self, message, key, scope):
        message = str(message)
        scope = str(scope)
        # r1, r2 \in_R Z_p
        r1 = Fr.from_random()
        r2 = Fr.from_random()

        sig = Signature()
        # nym = Hash(scp)*y
        h = hashlib.sha256(scope.encode())
        hscp = G1.from_hash(h.digest())
        sig.nym.set_object(hscp * key.y)

        # AA = A*r1
        sig.AA.set_object(key.A * r1)

        ## Good thing we precomputed much of this...
        # aux = (g1*h1^y*h2^s)^r1
        aux = (self.grpkey.g1 + key.H + key.h2s) * r1
        # A_ = AA*-x+(g1+h1*y+h2*s)*r1
        sig.A_.set_object((sig.AA * -key.x) + aux)

        # d = (g1+h1*y+h2*s)*r1+h2*-r2
        sig.d.set_object(aux + (self.grpkey.h2 * -r2))

        # r3 = r1**-1
        r3 = ~r1

        # ss = s - r2*r3
        ss = key.s - (r2 * r3)

        ## Auxiliar variables for the spk
        aux_Zr = -key.x
        ss = -ss
        negy = -key.y
        A_d = sig.A_ - sig.d

        y = [sig.nym, A_d, self.grpkey.g1]
        g = [hscp, sig.AA, self.grpkey.h2, sig.d, self.grpkey.h1]
        x = [aux_Zr, key.y, r2, r3, ss, negy]
        i = [
            (1, 0),  # hscp^y = (g[0],x[1])
            (0, 1),  # AA^-x = (g[1],x[0])
            (2, 2),  # h2^r2 = (g[2],x[2])
            (3, 3),  # d^r3 = (g[3],x[3])
            (4, 2),  # h2^-ss = (g[2],x[4])
            (5, 4),  # h1^-y = (g[4],x[5])
        ]
        prods = [1, 2, 3]
        pic, pis = spk.rep_sign(y, g, x, i, prods, message)
        sig.c.set_object(pic)
        sig.s.extend(pis)
        return sig

    def verify(self, message, signature, scope="def"):
        message = str(message)
        scope = str(scope)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        ## AA must not be 1 (since we use additive notation for G1,
        ## it must not be 0)
        if not sig.AA.is_zero():
            ## e(AA,ipk) must equal e(A_,g2)
            e1 = GT.pairing(sig.AA, self.grpkey.ipk)
            e2 = GT.pairing(sig.A_, self.grpkey.g2)
            if e1 == e2:
                ## Recompute hscp
                h = hashlib.sha256(scope.encode())
                hscp = G1.from_hash(h.digest())
                A_d = sig.A_ - sig.d
                y = [sig.nym, A_d, self.grpkey.g1]
                g = [hscp, sig.AA, self.grpkey.h2, sig.d, self.grpkey.h1]
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
                if spk.rep_verify(y, g, i, prods, sig.c, sig.s, message):
                    ret["status"] = "success"
                else:
                    ret["message"] = "spk.rep_verify failed"
                    logger.error(ret["message"])
            else:
                ret["message"] = "e1 != e2"
                logger.error(ret["message"])
        else:
            ret["message"] = "AA is zero"
            logger.error(ret["message"])
        return ret
