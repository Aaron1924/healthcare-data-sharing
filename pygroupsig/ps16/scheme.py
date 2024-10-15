import hashlib
from pygroupsig.pairings.mcl import Fr, G1, G2, GT
from pygroupsig.interfaces import SchemeInterface, ContainerInterface
from pygroupsig.baseclasses import B64Mixin
import pygroupsig.spk as spk
import logging


_NAME = "ps16"
_SEQ = 3
_START = 0


class GroupKey(B64Mixin, ContainerInterface):
    CTYPE = "group"

    def __init__(self):
        self.g = G1() # Random generator of G1
        self.gg = G2() # Random generator of G2
        self.X = G2() # gg^x (x is part of mgrkey)
        self.Y = G2() # gg^y (y is part of mgrkey)

    def info(self):
        return (_NAME, self.CTYPE), (
            "g", "gg",
            "X", "Y",
        )


class ManagerKey(B64Mixin, ContainerInterface):
    CTYPE = "manager"

    def __init__(self):
        self.x = Fr()
        self.y = Fr()

    def info(self):
        return (_NAME, self.CTYPE), ("x", "y")


class MemberKey(B64Mixin, ContainerInterface):
    CTYPE = "member"

    def __init__(self):
        self.sk = Fr()
        self.sigma1 = G1()
        self.sigma2 = G1()
        # TODO: remove e variable, not used
        self.e = GT() # e(sigma1,grpkey->Y)

    def info(self):
        return (_NAME, self.CTYPE), (
            "sk", "sigma1", "sigma2", "e"
        )


class Signature(B64Mixin, ContainerInterface):
    CTYPE = "signature"

    def __init__(self):
        self.sigma1 = G1()
        self.sigma2 = G1()
        self.c = Fr()
        self.s = Fr()

    def info(self):
        return (_NAME, self.CTYPE), (
            "sigma1", "sigma2",
            "c", "s"
        )


class Ps16(SchemeInterface):
    NAME = _NAME.upper()
    SEQ = _SEQ
    START = _START

    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = {}

    def setup(self):
        ## Set manager key
        self.mgrkey.x.set_random()
        self.mgrkey.y.set_random()

        ## Set group key
        self.grpkey.g.set_random()
        self.grpkey.gg.set_random()
        self.grpkey.X.set_object(self.grpkey.gg * self.mgrkey.x)
        self.grpkey.Y.set_object(self.grpkey.gg * self.mgrkey.y)

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
            ## Import the (n,tau,ttau,pi) ad hoc message
            n = G1.from_b64(message["n"])
            tau = G1.from_b64(message["tau"])
            ttau = G2.from_b64(message["ttau"])
            pic = Fr.from_b64(message["pic"])
            pis = Fr.from_b64(message["pis"])

            if spk.dlog_G1_verify(tau, self.grpkey.g,
                                  pic, pis, n.to_bytes()):
                e1 = GT.pairing(tau, self.grpkey.Y)
                e2 = GT.pairing(self.grpkey.g, ttau)

                if e1 == e2:
                    ## Compute the partial member key
                    u = Fr.from_random()
                    sigma1 = self.grpkey.g * u
                    aux = tau * self.mgrkey.y
                    sigma2 = self.grpkey.g * self.mgrkey.x
                    sigma2 = aux + sigma2
                    sigma2 = sigma2 * u

                    ## Add the tuple (i,tau,ttau) to the GML
                    h_id = hashlib.sha256()
                    h_id.update(tau.to_bytes())
                    h_id.update(ttau.to_bytes())
                    mem_id = h_id.hexdigest()
                    self.gml[mem_id] = (tau, ttau)

                    ## Mout = (sigma1,sigma2)
                    ret["status"] = "success"
                    ret["sigma1"] = sigma1.to_b64()
                    ret["sigma2"] = sigma2.to_b64()
                else:
                    ret["status"] = "fail"
                    ret["message"] = "e1 != e2"
                    logging.error(ret["message"])
            else:
                ret["status"] = "fail"
                ret["message"] = "spk.dlog_G1_verify failed"
                logging.error(ret["message"])
        else:
            ret["message"] = f"Phase not supported for {self.__class__.__name__}"
            logging.error(ret["message"])
        return ret

    def join_mem(self, phase, message, key):
        ret = {"status": "error"}
        if phase == 1:
            ## The manager sends a random element in G1
            n = G1.from_b64(message["n"])

            ## Compute secret exponent, tau and ttau
            key.sk.set_random()
            tau = self.grpkey.g * key.sk
            ttau = self.grpkey.Y * key.sk

            ## Compute the SPK for sk
            pic, pis = spk.dlog_G1_sign(
                tau, self.grpkey.g, key.sk, n.to_bytes())

            ## Build the output message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["tau"] = tau.to_b64()
            ret["ttau"] = ttau.to_b64()
            ret["pic"] = pic.to_b64()
            ret["pis"] = pis.to_b64()
        elif phase == 3:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                logging.error(ret["message"])
                return ret
            ## Check correctness of computation and update memkey

            # We have sk in memkey, so just need to copy the
            # sigma1, sigma2 and e values from the received message,
            # which is an exported (partial) memkey
            ## TODO: actually, e is not exported by join_mgr
            key.sigma1.set_b64(message["sigma1"])
            key.sigma2.set_b64(message["sigma2"])
            ret["status"] = "success"
        else:
            ret["message"] = f"Phase not supported for {self.__class__.__name__}"
            logging.error(ret["message"])
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
        e = GT.pairing(sig.sigma1, self.grpkey.Y)
        e = e ** k

        # c = hash(ps16_sig->sigma1,ps16_sig->sigma2,e,m)
        h = hashlib.sha256()
        h.update(sig.sigma1.to_bytes())
        h.update(sig.sigma2.to_bytes())
        h.update(e.to_bytes())
        h.update(message.encode())

        ## Complete the sig
        sig.c.set_hash(h.digest())
        sig.s.set_object(sig.c * key.sk)
        sig.s.set_object(k + sig.s)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)

        # e1 = e(sigma1^-1,X)
        aux_G1 = -sig.sigma1
        e1 = GT.pairing(aux_G1, self.grpkey.X)

        # e2 = e(sigma2,gg)
        e2 = GT.pairing(sig.sigma2, self.grpkey.gg)

        # e3 = e(sigma1^s,Y)
        aux_G1 = sig.sigma1 * sig.s
        e3 = GT.pairing(aux_G1, self.grpkey.Y)

        # R = (e1*e2)^-c*e3
        e1 = e1 * e2
        e1 = e1 ** sig.c
        e1 = ~e1
        e1 = e1 * e3

        h = hashlib.sha256()
        h.update(sig.sigma1.to_bytes())
        h.update(sig.sigma2.to_bytes())
        h.update(e1.to_bytes())
        h.update(message.encode())

        ## Complete the sig
        c = Fr.from_hash(h.digest())

        ## Compare the result with the received challenge
        if sig.c == c:
            ret["status"] = "success"
        else:
            ret["message"] = "sig.c != c"
            logging.error(ret["message"])
        return ret
