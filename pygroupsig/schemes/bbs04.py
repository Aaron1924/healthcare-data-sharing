import hashlib
import logging

from pygroupsig.helpers import B64Mixin, InfoMixin, ReprMixin
from pygroupsig.interfaces import (
    ContainerInterface,
    SchemeInterface,
)
from pygroupsig.pairings.mcl import G1, G2, GT, Fr

_NAME = "bbs04"
_SEQ = 1
_START = 0

logger = logging.getLogger(__name__)


class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g1 = G1()  # Tr(g2)
        self.g2 = G2()  # andom generator of G2
        self.h = G1()  # Random element in G1 \ 1
        self.u = G1()  # h^(xi1^-1) @see bbs04_mgr_key_t
        self.v = G1()  # h^(xi2^-1) @see bbs04_mgr_key_t
        self.w = G2()  # g2^gamma @see bbs04_mgr_key_t
        # Optimizations
        self.hw = GT()  # Precompute e(h,w)
        self.hg2 = GT()  # Precompute e(h,g2)
        self.g1g2 = GT()  # Precompute e(g1,g2)


class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.xi1 = Fr()  # Exponent for tracing signatures
        self.xi2 = Fr()  # Exponent for tracing signatures
        self.gamma = Fr()  # Exponent for generating member keys


class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.x = Fr()  # 1st element of the member's key
        self.A = G1()  # 2nd element of the member's key, A = g_1^(1/(gamma+x))
        self.Ag2 = GT()  # Optimizations, e(sigma1,grpkey->Y)


class Signature(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.T1 = G1()
        self.T2 = G1()
        self.T3 = G1()
        self.c = Fr()
        self.salpha = Fr()
        self.sbeta = Fr()
        self.sx = Fr()
        self.sdelta1 = Fr()
        self.sdelta2 = Fr()


class BBS04(ReprMixin, SchemeInterface):
    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = {}

    def setup(self):
        ## Select random generator g2 in G2. Since G2 is a cyclic multiplicative group
        ## of prime order, any element is a generator, so choose some random element.
        self.grpkey.g2.set_random()
        # @TODO g1 is supposed to be the trace of g2...
        self.grpkey.g1.set_random()

        # h random in G1 \ 1
        self.grpkey.h.set_random()
        ## why?
        while self.grpkey.h.is_zero():
            self.grpkey.h.set_random()

        # xi1 and xi2 random in Z^*_p
        self.mgrkey.xi1.set_random()
        self.mgrkey.xi2.set_random()

        # u = h*(xi1**-1)
        self.grpkey.u.set_object(self.grpkey.h * ~self.mgrkey.xi1)

        # v = h*(xi2**-1)
        self.grpkey.v.set_object(self.grpkey.h * ~self.mgrkey.xi2)

        # gamma random in Z^*_p
        self.mgrkey.gamma.set_random()

        # w = g_2*gamma
        self.grpkey.w.set_object(self.grpkey.g2 * self.mgrkey.gamma)

        # hw = e(h,w)
        self.grpkey.hw.set_object(GT.pairing(self.grpkey.h, self.grpkey.w))

        # hg2 = e(h, g2)
        self.grpkey.hg2.set_object(GT.pairing(self.grpkey.h, self.grpkey.g2))

        # g1g2 = e(g2, g2)
        self.grpkey.g1g2.set_object(GT.pairing(self.grpkey.g1, self.grpkey.g2))

    def join_mgr(self, phase, message=None):
        ret = {"status": "error"}
        if phase == 0:
            ## x \in_R Z_p^*
            x = Fr.from_random()

            ## Compute A = g_1 * ((mgrkey->gamma+x)**-1)
            A = self.grpkey.g1 * ~(self.mgrkey.gamma + x)

            ## Optimization
            Ag2 = GT.pairing(A, self.grpkey.g2)

            ## Update the GML
            h = hashlib.sha256(A.to_bytes())
            self.gml[h.hexdigest()] = (A,)

            ## Dump the key into a msg
            ret["status"] = "success"
            ret["x"] = x.to_b64()
            ret["A"] = A.to_b64()
            ret["Ag2"] = Ag2.to_b64()
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logger.error(ret["message"])
        return ret

    def join_mem(self, phase, message, key):
        ret = {"status": "error"}
        if phase == 1:
            ## Import the primitives sent by the manager
            key.x.set_b64(message["x"])
            key.A.set_b64(message["A"])
            key.Ag2.set_b64(message["Ag2"])

            ## Build the output message
            ret["status"] = "success"
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logger.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)

        # alpha,beta \in_R Zp
        alpha = Fr.from_random()
        beta = Fr.from_random()

        ## Compute T1,T2,T3
        # T1 = u*alpha
        sig = Signature()
        sig.T1.set_object(self.grpkey.u * alpha)
        # T2 = v*beta
        sig.T2.set_object(self.grpkey.v * beta)
        # T3 = A + h*(alpha+beta)
        alphabeta = alpha + beta
        sig.T3.set_object(key.A + (self.grpkey.h * alphabeta))

        # delta1 = x*alpha
        delta1 = key.x * alpha
        # delta2 = x*beta
        delta2 = key.x * beta

        # ralpha, rbeta, rx, rdelta1, rdelta2 \in_R Zp
        ralpha = Fr.from_random()
        rbeta = Fr.from_random()
        rx = Fr.from_random()
        rdelta1 = Fr.from_random()
        rdelta2 = Fr.from_random()

        ## Compute R1, R2, R3, R4, R5
        # Optimized o1 = e(T3, g2) = e(h, g2)**(alpha+beta) * e(A, g2)
        aux_o1 = (self.grpkey.hg2**alphabeta) * key.Ag2

        # R1 = u*ralpha
        R1 = self.grpkey.u * ralpha
        # R2 = v*rbeta
        R2 = self.grpkey.v * rbeta

        # R3 = e(T3,g2)^rx * e(h,w)^(-ralpha-rbeta) * e(h,g2)^(-rdelta1-rdelta2)
        # e1 = e(T3,g2)^rx
        aux_e1 = aux_o1**rx

        # e2 = e(h,w)**(-ralpha-rbeta)
        aux_e2 = self.grpkey.hw ** ((-ralpha) - rbeta)

        # e3 = e(h,g2)**(-rdelta1-rdelta2)
        aux_e3 = self.grpkey.hg2 ** ((-rdelta1) - rdelta2)

        # R3 = e1 * e2 * e3
        R3 = aux_e1 * aux_e2 * aux_e3

        # R4 = T1*rx + u*-rdelta1
        R4 = (sig.T1 * rx) + (self.grpkey.u * (-rdelta1))

        # R5 = T2*rx + v*-rdelta2
        R5 = (sig.T2 * rx) + (self.grpkey.v * (-rdelta2))

        # c = hash(M,T1,T2,T3,R1,R2,R3,R4,R5) \in Zp
        h = hashlib.sha256()
        h.update(message.encode())
        h.update(sig.T1.to_bytes())
        h.update(sig.T2.to_bytes())
        h.update(sig.T3.to_bytes())
        h.update(R1.to_bytes())
        h.update(R2.to_bytes())
        h.update(R3.to_bytes())
        h.update(R4.to_bytes())
        h.update(R5.to_bytes())

        ## Get c as the element associated to the obtained hash value
        sig.c.set_hash(h.digest())
        # salpha = ralpha + c*alpha
        sig.salpha.set_object(ralpha + (sig.c * alpha))
        # sbeta = rbeta + c*beta
        sig.sbeta.set_object(rbeta + (sig.c * beta))
        # sx = rx + c*x
        sig.sx.set_object(rx + (sig.c * key.x))
        # sdelta1 = rdelta1 + c*delta1
        sig.sdelta1.set_object(rdelta1 + (sig.c * delta1))
        # sdelta2 = rdelta2 + c*delta2
        sig.sdelta2.set_object(rdelta2 + (sig.c * delta2))

        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        # R1 = u*salpha + T1*(-c)
        aux_neg = -sig.c
        R1 = (self.grpkey.u * sig.salpha) + (sig.T1 * aux_neg)

        # R2 = v*sbeta + T2*(-c)
        R2 = (self.grpkey.v * sig.sbeta) + (sig.T2 * aux_neg)

        ## R3 = e(T3,g2)^sx * e(h,w)^(-salpha-sbeta) * e(h,g2)^(-sdelta1-sdelta2) * (e(T3,w)/e(g1,g2))^c
        ## Optimized R3 =  e(h,w)^(-salpha-sbeta) * e(h,g2)^(-sdelta1-sdelta2) * e(T3, w^c * g2 ^ sx) * e(g1, g2)^-c

        ## Optimized e1 = e(T3, g2*sx + w*c)
        aux_e5 = (self.grpkey.g2 * sig.sx) + (self.grpkey.w * sig.c)
        aux_e1 = GT.pairing(sig.T3, aux_e5)

        # e2 = e(h,w)**(-salpha-sbeta)
        aux_neg = (-sig.salpha) - sig.sbeta
        aux_e2 = self.grpkey.hw**aux_neg

        # e3 = e(h,g2)**(-sdelta1-sdelta2)
        aux_neg = (-sig.sdelta1) - sig.sdelta2
        aux_e3 = self.grpkey.hg2**aux_neg

        # e4 = e(g1,g2)**-c
        aux_e4 = ~(self.grpkey.g1g2**sig.c)

        # R3 = e1 * e2 * e3 * e4
        R3 = aux_e1 * aux_e2 * aux_e3 * aux_e4

        # R4 = T1*sx + u*(-sdelta1)
        R4 = (sig.T1 * sig.sx) + (self.grpkey.u * (-sig.sdelta1))

        # R5 = T2*sx + v*(-sdelta2)
        R5 = (sig.T2 * sig.sx) + (self.grpkey.v * (-sig.sdelta2))

        ## Recompute the hash-challenge c
        # c = hash(M,T1,T2,T3,R1,R2,R3,R4,R5) \in Zp
        h = hashlib.sha256()
        h.update(message.encode())
        h.update(sig.T1.to_bytes())
        h.update(sig.T2.to_bytes())
        h.update(sig.T3.to_bytes())
        h.update(R1.to_bytes())
        h.update(R2.to_bytes())
        h.update(R3.to_bytes())
        h.update(R4.to_bytes())
        h.update(R5.to_bytes())

        c = Fr.from_hash(h.digest())

        ## Compare the result with the received challenge
        if sig.c == c:
            ret["status"] = "success"
        else:
            ret["message"] = "sig.c != c"
            logger.error(ret["message"])
        return ret

    def open(self, signature):
        ret = {"status": "fail"}
        ## Recover the signer's A as
        sig = Signature.from_b64(signature)
        # A = T3 - (T1*xi1 + T2*xi2)
        A = sig.T3 - ((sig.T1 * self.mgrkey.xi1) + (sig.T2 * self.mgrkey.xi2))
        h = hashlib.sha256(A.to_bytes())
        mem_id = h.hexdigest()
        if mem_id in self.gml:
            ret["status"] = "success"
            ret["id"] = mem_id
        return ret
