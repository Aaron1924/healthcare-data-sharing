import hashlib
import logging
import time

import pygroupsig.spk as spk
from pygroupsig.baseclasses import B64Mixin, InfoMixin
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.pairings.mcl import G1, G2, GT, Fr

_NAME = "gl19"
_SEQ = 3
_START = 0


class GroupKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g1 = G1()  # Random generator of G1
        self.g2 = G2()  # Random generator of G2
        self.g = G1()  # Random generator of G1
        self.h = G1()  # Random generator of G1
        self.h1 = G1()  # Random generator of G1
        self.h2 = G1()  # Random generator of G1
        self.h3 = G1()  # Random generator of G1. Used for setting expiration date of member creds
        self.ipk = G2()  # Issuer public key
        self.cpk = G1()  # Converter public key
        self.epk = G1()  # Extractor public key


class ManagerKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.isk = Fr()  # Issuer secret key
        self.csk = Fr()  # Converter secret key
        self.esk = Fr()  # Extractor secret key


class MemberKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.A = G1()  # A = (H*h2^s*g1)^(1/isk+x)
        self.x = Fr()  # Randomly picked by the Issuer
        self.y = Fr()  # Randomly picked by the Member
        self.s = Fr()  # Randomly picked by the Issuer
        self.l = -1  # Lifetime of the credential (UNIX time seconds)
        self.d = Fr()  # Fr element mapped from Hash(lifetime)
        self.H = G1()  # Member's "public key". H = h1^y
        self.h2s = G1()  # Used in signatures. h2s = h2^s
        self.h3d = G1()  # Used in signatures. h3d = h3^d


class Signature(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.AA = G1()
        self.A_ = G1()
        self.d = G1()
        self.c = Fr()
        self.s = []
        self.nym1 = G1()
        self.nym2 = G1()
        self.ehy1 = G1()
        self.ehy2 = G1()
        self.expiration = -1
        # Expiration date. This is metainformation actually
        # pertaining to the signer's credential. The verify
        # process checks that the signature was produced by a
        # signer controlling a credential with the corresponding
        # expiration date


class Gl19(SchemeInterface):
    LIFETIME = 60 * 60 * 24 * 14  # two weeks
    # TODO: add lifetime setter

    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = {}

    def setup(self):
        ## Initializes the Manager key
        self.mgrkey.isk.set_random()

        ## Initializes the Group key
        # Compute random generators g1, g, h, h1 and h2 in G1. Since G1 is a cyclic
        # group of prime order, just pick random elements
        self.grpkey.g1.set_random()
        self.grpkey.g.set_random()
        self.grpkey.h.set_random()
        self.grpkey.h1.set_random()
        self.grpkey.h2.set_random()
        self.grpkey.h3.set_random()

        ## Compute random generator g2 in G2. Since G2 is a cyclic group of prime
        ## order, just pick a random element
        self.grpkey.g2.set_random()

        ## Add the Issuer's public key to the group key
        self.grpkey.ipk.set_object(self.grpkey.g2 * self.mgrkey.isk)

        ## Generate the Converter's private key
        self.mgrkey.csk.set_random()

        ## Add the Converter's public key to the group key
        self.grpkey.cpk.set_object(self.grpkey.g * self.mgrkey.csk)

        ## Generate the Extractor's private key
        self.mgrkey.esk.set_random()

        ## Add the Extractor's public key to the group key
        self.grpkey.epk.set_object(self.grpkey.g * self.mgrkey.esk)

    def join_mgr(self, phase, message=None):
        ret = {"status": "error"}
        if phase == 0:
            ## Send a random element to the member
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ## TODO: This value should be saved in some place to avoid replay attack
        elif phase == 2:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                logging.error(ret["message"])
                return ret
            ## Compute credential from H and pi_H. Verify the proof
            n = G1.from_b64(message["n"])
            H = G1.from_b64(message["H"])
            pic = Fr.from_b64(message["pic"])
            pis = Fr.from_b64(message["pis"])

            if spk.dlog_G1_verify(H, self.grpkey.h1, pic, pis, n.to_bytes()):
                ## Pick x and s at random from Z*_p
                x = Fr.from_random()
                s = Fr.from_random()

                life = str(int(time.time() + self.LIFETIME))
                h = hashlib.sha256(life.encode()).digest()
                ## Modification w.r.t. the GL19 paper: we add a maximum lifetime
                ## for member credentials. This is done by adding a second message
                ## to be signed in the BBS+ signatures. This message will then be
                ## "revealed" (i.e., shared in cleartext) in the SPK computed for
                ## signing
                d = Fr.from_hash(h)

                ## Set A = (H*h_2^s*h3^d*g_1)^(1/isk+x)
                h2s = G1.from_object(self.grpkey.h2 * s)
                h3d = G1.from_object(self.grpkey.h3 * d)
                A = h2s + self.grpkey.g1
                A = A + h3d
                A = A + H
                aux = self.mgrkey.isk + x
                aux = ~aux
                A = A * aux

                ## Mout = (A,x,s,l)
                ret["status"] = "success"
                ret["A"] = A.to_b64()
                ret["x"] = x.to_b64()
                ret["s"] = s.to_b64()
                ret["l"] = life
            else:
                ret["status"] = "fail"
                ret["message"] = "spk.dlog_G1_verify failed"
                logging.error(ret["message"])
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logging.error(ret["message"])
        return ret

    def join_mem(self, phase, message, key):
        ret = {"status": "error"}
        if phase == 1:
            ## Parse n and compute (Y,\pi_Y)
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
        elif phase == 3:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                logging.error(ret["message"])
                return ret
            ## Check correctness of computation and update memkey

            # Min = (A,x,s,l)
            key.A.set_b64(message["A"])
            key.x.set_b64(message["x"])
            key.s.set_b64(message["s"])
            key.l = int(message["l"])

            ## Recompute h2s from s
            key.h2s.set_object(self.grpkey.h2 * key.s)

            ## Recompute d and h3d from l
            h = hashlib.sha256(str(key.l).encode()).digest()
            key.d.set_hash(h)
            key.h3d.set_object(self.grpkey.h3 * key.d)

            ## Check correctness
            # A must not be 1 (since we use additive notation for G1,
            # it must not be 0)
            if not key.A.is_zero():
                e1 = GT.pairing(key.A, self.grpkey.g2)
                e1 = e1**key.x
                e2 = GT.pairing(key.A, self.grpkey.ipk)
                e1 = e1 * e2
                aux = key.h2s + key.h3d
                aux = aux + key.H
                aux = aux + self.grpkey.g1
                e3 = GT.pairing(aux, self.grpkey.g2)
                if e1 == e3:
                    ret["status"] = "success"
                else:
                    ret["status"] = "fail"
                    ret["message"] = "e1 != e3"
                    logging.error(ret["message"])
            else:
                ret["status"] = "fail"
                ret["message"] = "A is zero"
                logging.error(ret["message"])
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logging.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)
        # alpha, r1, r2 \in_R Z_p
        alpha = Fr.from_random()
        r1 = Fr.from_random()
        r2 = Fr.from_random()

        # nym1 = g1^alpha
        sig = Signature()
        sig.nym1.set_object(self.grpkey.g * alpha)

        # nym2 = cpk^alpha*h^y
        aux1 = self.grpkey.cpk * alpha
        aux2 = self.grpkey.h * key.y
        sig.nym2.set_object(aux1 + aux2)

        ## Add extra encryption of h^y with epk
        alpha2 = Fr.from_random()

        # ehy1 = g1^alpha2
        sig.ehy1.set_object(self.grpkey.g * alpha2)

        # ehy2 = epk^alpha2*h^y
        aux1 = self.grpkey.epk * alpha2
        aux2 = self.grpkey.h * key.y
        sig.ehy2.set_object(aux1 + aux2)

        # AA = A^r1
        sig.AA.set_object(key.A * r1)

        # A_ = AA^{-x}(g1*h1^y*h2^s*h3d)^r1
        ## Good thing we precomputed much of this...
        aux = key.H + key.h2s
        aux = self.grpkey.g1 + aux
        aux = key.h3d + aux
        # aux = (g1*h1^y*h2^s*h3^d)^r1
        aux = aux * r1
        aux_Zr = -key.x
        aux1 = sig.AA * aux_Zr
        sig.A_.set_object(aux1 + aux)

        # d = (g1*h1^y*h2^s*h3^d)^r1*h2^{-r2}
        aux_Zr = -r2
        aux1 = self.grpkey.h2 * aux_Zr
        sig.d.set_object(aux + aux1)

        # r3 = r1^{-1}
        r3 = ~r1

        # ss = s - r2*r3
        aux_Zr = r2 * r3
        ss = key.s - aux_Zr

        ## Auxiliar variables for the spk
        aux_Zr = -key.x
        ss = -ss
        negy = -key.y
        A_d = sig.A_ - sig.d

        # g1h3d = g1*h3^d
        g1h3d = self.grpkey.g1 + key.h3d

        y = [sig.nym1, sig.nym2, A_d, g1h3d, sig.ehy1, sig.ehy2]
        g = [
            self.grpkey.g,
            self.grpkey.cpk,
            self.grpkey.h,
            sig.AA,
            self.grpkey.h2,
            sig.d,
            self.grpkey.h1,
            self.grpkey.epk,
        ]
        x = [aux_Zr, key.y, r2, r3, ss, alpha, negy, alpha2]
        i = [
            (5, 0),  # alpha, g
            (5, 1),  # alpha, cpk
            (1, 2),  # y, h
            (0, 3),  # -x, AA
            (2, 4),  # r2, h2
            (3, 5),  # r3, d
            (4, 4),  # ss, h2
            (6, 6),  # -y, h1
            (7, 0),  # alpha2, g
            (7, 7),  # alpha2, epk
            (1, 2),
        ]  # y, h
        prods = [1, 2, 2, 3, 1, 2]

        ## The SPK'ed message becomes the message to sign concatenated with the
        ## credential expiration date
        sig.expiration = key.l
        pic, pis = spk.rep_sign(
            y, g, x, i, prods, f"{sig.expiration}|{message}"
        )
        sig.c.set_object(pic)
        sig.s.extend(pis)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        ## Auxiliar variables for the spk
        A_d = sig.A_ - sig.d

        ## The last sizeof(uint64_t) bytes of the message contain the expiration
        ## date. Parse them, and recompute the h3d value, needed to verify the SPK

        h = hashlib.sha256(str(sig.expiration).encode()).digest()
        expiration = Fr.from_hash(h)
        g1h3d = (self.grpkey.h3 * expiration) + self.grpkey.g1

        y = [sig.nym1, sig.nym2, A_d, g1h3d, sig.ehy1, sig.ehy2]
        g = [
            self.grpkey.g,
            self.grpkey.cpk,
            self.grpkey.h,
            sig.AA,
            self.grpkey.h2,
            sig.d,
            self.grpkey.h1,
            self.grpkey.epk,
        ]
        i = [
            (5, 0),  # alpha, g
            (5, 1),  # alpha, cpk
            (1, 2),  # y, h
            (0, 3),  # -x, AA
            (2, 4),  # r2, h2
            (3, 5),  # r3, d
            (4, 4),  # ss, h2
            (6, 6),  # -y, h1
            (7, 0),  # alpha2, g
            (7, 7),  # alpha2, epk
            (1, 2),
        ]  # y, h
        prods = [1, 2, 2, 3, 1, 2]

        ## Verify SPK
        if spk.rep_verify(
            y, g, i, prods, sig.c, sig.s, f"{sig.expiration}|{message}"
        ):
            ret["status"] = "success"
        else:
            ret["message"] = "spk.dlog_G1_verify failed"
            logging.error(ret["message"])
        return ret
