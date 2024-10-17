import hashlib
import json
import logging

import pygroupsig.spk as spk
from pygroupsig.baseclasses import B64Mixin, InfoMixin
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.pairings.mcl import G1, G2, GT, Fr

_NAME = "klap20"
_SEQ = 3
_START = 0


class GroupKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "group"

    def __init__(self):
        self.g = G1()  # Random generator of G1
        self.gg = G2()  # Random generator of G1
        self.XX = G2()  # gg^x (x is part of mgrkey)
        self.YY = G2()  # gg^y (y is part of mgrkey)
        self.ZZ0 = G2()  # gg^z0 (z0 is part of mgrkey)
        self.ZZ1 = G2()  # gg^z1 (z1 is part of mgrkey)


class ManagerKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.x = Fr()  # Issuer component x
        self.y = Fr()  # Issuer component y
        self.z0 = Fr()  # Opener component z_0
        self.z1 = Fr()  # Opener component z_1


class MemberKey(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "member"

    def __init__(self):
        self.alpha = Fr()
        self.u = G1()
        self.v = G1()
        self.w = G1()


class Signature(B64Mixin, InfoMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.uu = G1()
        self.vv = G1()
        self.ww = G1()
        self.c = Fr()
        self.s = Fr()


class Klap20(SchemeInterface):
    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()
        self.gml = {}

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
            ## Import the (n,f,w,SSO,SS1,ff0,ff1,pic,pis) ad hoc message
            n = G1.from_b64(message["n"])
            f = G1.from_b64(message["f"])
            w = G1.from_b64(message["w"])
            SS0 = G2.from_b64(message["SS0"])
            SS1 = G2.from_b64(message["SS1"])
            ff0 = G2.from_b64(message["ff0"])
            ff1 = G2.from_b64(message["ff1"])
            pic = Fr.from_b64(message["pic"])
            pis = [Fr.from_b64(el) for el in json.loads(message["pis"])]
            ## Check the SPK -- this will change with issue23
            ## Compute the SPK for sk -- this will be replaced in issue23
            # u = Hash(f)
            h = hashlib.sha256(f.to_bytes()).digest()
            u = G1.from_hash(h)

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
            if spk.verify(y, g, i, prods, pic, pis, n.to_bytes()):
                w = w * self.mgrkey.y
                u = u * self.mgrkey.x
                v = u + w
                # Add the tuple (i,SS0,SS1,ff0,ff1,tau) to the GML
                tau = GT.pairing(f, self.grpkey.gg)
                # Currently, KLAP20 identities are just uint64_t's
                h_id = hashlib.sha256()
                h_id.update(SS0.to_bytes())
                h_id.update(SS1.to_bytes())
                h_id.update(ff0.to_bytes())
                h_id.update(ff1.to_bytes())
                h_id.update(tau.to_bytes())
                mem_id = h_id.hexdigest()
                self.gml[mem_id] = (SS0, SS1, ff0, ff1, tau)
                ret["status"] = "success"
                ret["v"] = v.to_b64()
            else:
                ret["status"] = "fail"
                ret["message"] = "spk.verify failed"
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
            ## The manager sends a random element in G1
            n = G1.from_b64(message["n"])

            ## Compute secret alpha, s0 and s1
            key.alpha.set_random()

            s0 = Fr.from_random()
            s1 = Fr.from_random()

            # f = g^alpha
            f = G1.from_object(self.grpkey.g * key.alpha)
            # u = Hash(f)
            h = hashlib.sha256(f.to_bytes()).digest()
            key.u.set_hash(h)

            # w = u^alpha
            key.w.set_object(key.u * key.alpha)

            # SS0 = gg^s0
            SS0 = G2.from_object(self.grpkey.gg * s0)

            # SS1 = gg^s1
            SS1 = G2.from_object(self.grpkey.gg * s1)

            # ff0 = gg^alpha*ZZ0^s0
            ggalpha = G2.from_object(self.grpkey.gg * key.alpha)
            ZZ0s0 = G2.from_object(self.grpkey.ZZ0 * s0)
            ff0 = G2.from_object(ggalpha + ZZ0s0)

            # ff1 = gg^alpha*ZZ1^s1
            ZZ1s1 = G2.from_object(self.grpkey.ZZ1 * s1)
            ff1 = G2.from_object(ggalpha + ZZ1s1)

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
                (2, 4),
            ]  # s1, ZZ1
            prods = [1, 1, 1, 1, 2, 2]
            pic, pis = spk.sign(y, g, x, i, prods, n.to_bytes())
            ## Need to send (n, f, w, SS0, SS1, ff0, ff1, pi): prepare ad hoc message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["f"] = f.to_b64()
            ret["w"] = key.w.to_b64()
            ret["SS0"] = SS0.to_b64()
            ret["SS1"] = SS1.to_b64()
            ret["ff0"] = ff0.to_b64()
            ret["ff1"] = ff1.to_b64()
            ret["pic"] = pic.to_b64()
            ret["pis"] = json.dumps([p.to_b64() for p in pis])
        elif phase == 3:
            if not isinstance(message, dict):
                ret["message"] = "Invalid message type. Expected dict"
                logging.error(ret["message"])
                return ret
            # Min = v
            key.v = G1.from_b64(message["v"])
            # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
            e1 = GT.pairing(key.v, self.grpkey.gg)
            e2 = GT.pairing(key.u, self.grpkey.XX)
            e3 = GT.pairing(key.w, self.grpkey.YY)
            e2 = e2 * e3
            if e1 == e2:
                ret["status"] = "success"
            else:
                ret["status"] = "fail"
                ret["message"] = "e1 != e2"
                logging.error(ret["message"])
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            logging.error(ret["message"])
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
        pic, pis = spk.dlog_G1_sign(sig.ww, sig.uu, key.alpha, message)
        sig.c.set_object(pic)
        sig.s.set_object(pis)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        message = str(message)
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        ## Verify SPK
        if spk.dlog_G1_verify(sig.ww, sig.uu, sig.c, sig.s, message):
            # e1 = e(vv,gg)
            e1 = GT.pairing(sig.vv, self.grpkey.gg)
            # e2 = e(uu,XX)
            e2 = GT.pairing(sig.uu, self.grpkey.XX)
            # e3 = e(ww,YY)
            e3 = GT.pairing(sig.ww, self.grpkey.YY)
            e2 = e2 * e3
            ## Compare the result with the received challenge
            if e1 == e2:
                ret["status"] = "success"
            else:
                ret["message"] = "e1 != e2"
                logging.error(ret["message"])
        else:
            ret["message"] = "spk.dlog_G1_verify failed"
            logging.error(ret["message"])
        return ret
