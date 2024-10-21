import hashlib
import logging

from pygroupsig.baseclasses import B64Mixin, InfoMixin
from pygroupsig.interfaces import (
    ContainerInterface,
    SchemeInterface,
)
from pygroupsig.pairings.mcl import G1, G2, GT, Fr

_NAME = "bbs04"
_SEQ = 1
_START = 0


class GroupKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g1 = G1()  # Tr(g2)
        self.g2 = G2()  # andom generator of G2
        self.h = G1()  # Random element in G1 \ 1
        self.u = G1()  # h^(xi1^-1) @see bbs04_mgr_key_t
        self.v = G1()  # h^(xi2^-1) @see bbs04_mgr_key_t
        self.w = G2()  # g2^gamma @see bbs04_mgr_key_t
        self.hw = GT()  # Precompute e(h,w)
        self.hg2 = GT()  # Precompute e(h,g2)
        self.g1g2 = GT()  # Precompute e(g1,g2)


class ManagerKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.xi1 = Fr()  # Exponent for tracing signatures
        self.xi2 = Fr()  # Exponent for tracing signatures
        self.gamma = Fr()  # Exponent for generating member keys


class MemberKey(B64Mixin, InfoMixin, ContainerInterface):
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


class Bbs04(SchemeInterface):
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

        # u = h^(1/xi1)
        inv = ~self.mgrkey.xi1
        self.grpkey.u.set_object(self.grpkey.h * inv)

        # v = h^(1/xi2)
        inv = ~self.mgrkey.xi2
        self.grpkey.v.set_object(self.grpkey.h * inv)

        # gamma random in Z^*_p
        self.mgrkey.gamma.set_random()

        # w = g_2^gamma
        self.grpkey.w.set_object(self.grpkey.g2 * self.mgrkey.gamma)

        ## Optimizations
        # hw = e(h,w)
        self.grpkey.hw.set_object(GT.pairing(self.grpkey.h, self.grpkey.w))

        # hg2 = e(h, g2)
        self.grpkey.hg2.set_object(GT.pairing(self.grpkey.h, self.grpkey.g2))

        # g1g2 = e(g2, g2)
        self.grpkey.g1g2.set_object(GT.pairing(self.grpkey.g1, self.grpkey.g2))

    def join_mgr(self, phase, message=None):
        ret = {"status": "error"}
        if phase == 0:
            ## Select memkey->x randomly in Z_p^*
            key = MemberKey()
            key.x.set_random()

            ## Compute memkey->A = g_1^(1/(mgrkey->gamma+memkey->x))
            gammax = self.mgrkey.gamma + key.x

            key.A.set_object(self.grpkey.g1)
            gammax = ~gammax
            key.A.set_object(key.A * gammax)

            ## Optimization
            key.Ag2.set_object(GT.pairing(key.A, self.grpkey.g2))

            ## Update the GML
            mem_id = hashlib.sha256(key.A.to_bytes()).hexdigest()
            self.gml[mem_id] = key.A

            ## Dump the key into a msg
            ret["status"] = "success"
            ret["key"] = key.to_b64()
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logging.error(ret["message"])
        return ret

    def join_mem(self, phase, message, key):
        ret = {"status": "error"}
        if phase == 1:
            ## This is mainly an utility function to keep uniformity across schemes:
            ## Just import the memkey from the received message and copy it into the
            ## provided memkey
            key.set_b64(message["key"])

            ## Build the output message
            ret["status"] = "success"
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logging.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)

        # alpha,beta \in_R Zp
        alpha = Fr.from_random()
        beta = Fr.from_random()

        ## Compute T1,T2,T3
        # T1 = u^alpha
        sig = Signature()
        sig.T1.set_object(self.grpkey.u * alpha)

        # T2 = v^beta
        sig.T2.set_object(self.grpkey.v * beta)

        # T3 = A*h^(alpha+beta)
        alphabeta = alpha + beta
        sig.T3.set_object(self.grpkey.h * alphabeta)
        sig.T3.set_object(key.A + sig.T3)

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
        # Optimized o1 = e(T3, g2) = e(A, g2) * e(h, g2) ^ alpha + beta
        aux_o1 = self.grpkey.hg2**alphabeta
        aux_o1 = aux_o1 * key.Ag2

        # R1 = u^ralpha
        R1 = self.grpkey.u * ralpha

        # R2 = v^rbeta
        R2 = self.grpkey.v * rbeta

        # R3 = e(T3,g2)^rx * e(h,w)^(-ralpha-rbeta) * e(h,g2)^(-rdelta1-rdelta2)
        # e1 = e(T3,g2)^rx
        aux_e1 = aux_o1**rx

        # e2 = e(h,w)^(-ralpha-rbeta)
        aux_Fr = -ralpha
        aux_Fr = aux_Fr - rbeta
        aux_e2 = self.grpkey.hw**aux_Fr

        # e3 = e(h,g2)^(-rdelta1-rdelta2)
        aux_Fr = -rdelta1
        aux_Fr = aux_Fr - rdelta2
        aux_e3 = self.grpkey.hg2**aux_Fr

        # R3 = e1 * e2 * e3
        R3 = aux_e1 * aux_e2
        R3 = R3 * aux_e3

        # R4 = T1^rx * u^-rdelta1
        R4 = sig.T1 * rx
        aux_Fr = -rdelta1
        aux_G1 = self.grpkey.u * aux_Fr
        R4 = R4 + aux_G1

        # R5 = T2^rx * v^-rdelta2
        R5 = sig.T2 * rx
        aux_Fr = -rdelta2
        aux_G1 = self.grpkey.v * aux_Fr
        R5 = R5 + aux_G1

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
        # salpha = ralpha + c*alpha
        sig.c.set_object(Fr.from_hash(h.digest()))
        sig.salpha.set_object(sig.c * alpha)
        sig.salpha.set_object(sig.salpha + ralpha)

        # sbeta = rbeta + c*beta
        sig.sbeta.set_object(sig.c * beta)
        sig.sbeta.set_object(sig.sbeta + rbeta)

        # sx = rx + c*x
        sig.sx.set_object(sig.c * key.x)
        sig.sx.set_object(sig.sx + rx)

        # sdelta1 = rdelta1 + c*delta1
        sig.sdelta1.set_object(sig.c * delta1)
        sig.sdelta1.set_object(sig.sdelta1 + rdelta1)

        # sdelta2 = rdelta2 + c*delta2
        sig.sdelta2.set_object(sig.c * delta2)
        sig.sdelta2.set_object(sig.sdelta2 + rdelta2)

        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        # R1 = u^salpha * T1^(-c)
        aux_neg = -sig.c
        R1 = self.grpkey.u * sig.salpha
        aux_G1 = sig.T1 * aux_neg
        R1 = R1 + aux_G1

        # R2 = v^sbeta * T2^(-c)
        R2 = self.grpkey.v * sig.sbeta
        aux_G1 = sig.T2 * aux_neg
        R2 = R2 + aux_G1

        ## R3 = e(T3,g2)^sx * e(h,w)^(-salpha-sbeta) * e(h,g2)^(-sdelta1-sdelta2) * (e(T3,w)/e(g1,g2))^c
        ## Optimized R3 =  e(h,w)^(-salpha-sbeta) * e(h,g2)^(-sdelta1-sdelta2) * e(T3, w^c * g2 ^ sx) * e(g1, g2)^-c

        ## Optimized e1 = e(T3, w^c * g2 ^ sx)
        aux_e5 = self.grpkey.w * sig.c
        aux_G2 = self.grpkey.g2 * sig.sx
        aux_e5 = aux_G2 + aux_e5
        aux_e1 = GT.pairing(sig.T3, aux_e5)

        # e2 = e(h,w)^(-salpha-sbeta)
        aux_neg = -sig.salpha
        aux_neg = aux_neg - sig.sbeta
        aux_e2 = self.grpkey.hw**aux_neg

        # e3 = e(h,g2)^(-sdelta1-sdelta2)
        aux_neg = -sig.sdelta1
        aux_neg = aux_neg - sig.sdelta2
        aux_e3 = self.grpkey.hg2**aux_neg

        # e4 = e(g1,g2)^-c
        aux_e4 = self.grpkey.g1g2**sig.c
        aux_e4 = ~aux_e4

        # R3 = e1 * e2 * e3 * e4
        R3 = aux_e1 * aux_e2
        R3 = R3 * aux_e3
        R3 = R3 * aux_e4

        # R4 = T1^sx * u^(-sdelta1)
        aux_neg = -sig.sdelta1
        aux_G1 = sig.T1 * sig.sx
        R4 = self.grpkey.u * aux_neg
        R4 = R4 + aux_G1

        # R5 = T2^sx * v^(-sdelta2)
        aux_neg = -sig.sdelta2
        aux_G1 = sig.T2 * sig.sx
        R5 = self.grpkey.v * aux_neg
        R5 = aux_G1 + R5

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
            logging.error(ret["message"])
        return ret
