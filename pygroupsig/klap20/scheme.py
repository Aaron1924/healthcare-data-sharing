import json
import hashlib
from pygroupsig.pairings.mcl import Fr, G1, G2, GT
from pygroupsig.interfaces import SchemeInterface, KeyInterface, SignatureInterface
# from pygroupsig.definitions import SPKRep
import logging
from base64 import b64encode, b64decode


class GroupKey(KeyInterface):
    def __init__(self):
        self.g = G1()
        self.gg = G2()
        self.XX = G2()
        self.YY = G2()
        self.ZZ0 = G2()
        self.ZZ1 = G2()


class ManagerKey(KeyInterface):
    def __init__(self):
        self.x = Fr()
        self.y = Fr()
        self.z0 = Fr()
        self.z1 = Fr()


class MemberKey(KeyInterface):
    def __init__(self):
        self.alpha = Fr()
        self.u = G1()
        self.v = G1()
        self.w = G1()


class Signature(SignatureInterface):
    def __init__(self):
        self.uu = G1()
        self.vv = G1()
        self.ww = G1()
        self.c = Fr()
        self.s = Fr()

    def to_b64(self):
        dump = {
            "uu": self.uu.to_b64(),
            "vv": self.vv.to_b64(),
            "ww": self.ww.to_b64(),
            "c": self.c.to_b64(),
            "s": self.s.to_b64(),
        }
        return b64encode(json.dumps(dump).encode()).decode()

    def set_b64(self, s):
        data = json.loads(b64decode(s.encode()))
        self.uu.set_b64(data["uu"])
        self.vv.set_b64(data["vv"])
        self.ww.set_b64(data["ww"])
        self.c.set_b64(data["c"])
        self.s.set_b64(data["s"])

    @classmethod
    def from_b64(cls, s):
        ret = cls()
        ret.set_b64(s)
        return ret


class Klap20(SchemeInterface):
    NAME = "KLAP20"
    SEQ = 3
    START = 0

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

    def join_mgr(self, phase, message):
        ret = {"status": "error"}
        if phase == 0:
            ## Send a random element to the member
            n = G1.from_random()
            ret["status"] = "success"
            ret["n"] = n.to_b64()
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
            h = hashlib.blake2s(f.to_bytes()).digest()
            u = G1.from_hash(h)

            y = [f, w, SS0, SS1, ff0, ff1]
            g = [self.grpkey.g, u, self.grpkey.gg,
                 self.grpkey.ZZ0, self.grpkey.ZZ1]
            i = [(0, 0), # alpha, g
                 (0, 1), # alpha, u
                 (1, 2), # s0, gg
                 (2, 2), # s1, gg
                 (0, 2), # alpha, gg
                 (1, 3), # s0, ZZ0
                 (0, 2), # alpha, gg
                 (2, 4)] # s1, ZZ1
            prods = [1, 1, 1, 1, 2, 2]
            if spk0_verify(y, g, i, prods, pic, pis, n.to_bytes()):
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
                ret["message"] = "spk0_verify failed"
                logging.error(ret["message"])
        else:
            ret["message"] = f"Phase not supported for {self.__class__.__name__}"
            logging.error(ret["message"])
        return ret

    def join_mem(self, phase, message):
        ret = {"status": "error"}
        if phase == 1:
            ## The manager sends a random element in G1
            n = G1.from_b64(message["n"])

            ## Compute secret alpha, s0 and s1
            self.memkey = MemberKey()
            self.memkey.alpha.set_random()

            s0 = Fr.from_random()
            s1 = Fr.from_random()

            # f = g^alpha
            f = G1.from_object(self.grpkey.g * self.memkey.alpha)
            # u = Hash(f)
            ## TODO, benckmark blake2s vs blake2b speed depending of the CPU
            h = hashlib.blake2s(f.to_bytes()).digest()
            self.memkey.u.set_hash(h)

            # w = u^alpha
            self.memkey.w.set_object(self.memkey.u * self.memkey.alpha)

            # SS0 = gg^s0
            SS0 = G2.from_object(self.grpkey.gg * s0)

            # SS1 = gg^s1
            SS1 = G2.from_object(self.grpkey.gg * s1)

            # ff0 = gg^alpha*ZZ0^s0
            ggalpha = G2.from_object(self.grpkey.gg * self.memkey.alpha)
            ZZ0s0 = G2.from_object(self.grpkey.ZZ0 * s0)
            ff0 = G2.from_object(ggalpha + ZZ0s0)

            # ff1 = gg^alpha*ZZ1^s1
            ZZ1s1 = G2.from_object(self.grpkey.ZZ1 * s1)
            ff1 = G2.from_object(ggalpha + ZZ1s1)

            # tau = e(f,gg)
            # tau = GT.pairing(f, self.grpkey.gg)
            ## TODO: Whats the usage of tau in this current phase?

            y = [f, self.memkey.w, SS0, SS1, ff0, ff1]
            g = [self.grpkey.g, self.memkey.u, self.grpkey.gg,
                 self.grpkey.ZZ0, self.grpkey.ZZ1]
            x = [self.memkey.alpha, s0, s1]
            i = [(0, 0), # alpha, g
                 (0, 1), # alpha, u
                 (1, 2), # s0, gg
                 (2, 2), # s1, gg
                 (0, 2), # alpha, gg
                 (1, 3), # s0, ZZ0
                 (0, 2), # alpha, gg
                 (2, 4)] # s1, ZZ1
            prods = [1, 1, 1, 1, 2, 2]
            pic, pis = spk0_sign(y, g, x, i, prods, n.to_bytes())
            ## Need to send (n, f, w, SS0, SS1, ff0, ff1, pi): prepare ad hoc message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["f"] = f.to_b64()
            ret["w"] = self.memkey.w.to_b64()
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
            self.memkey.v = G1.from_b64(message["v"])
            # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
            e1 = GT.pairing(self.memkey.v, self.grpkey.gg)
            e2 = GT.pairing(self.memkey.u, self.grpkey.XX)
            e3 = GT.pairing(self.memkey.w, self.grpkey.YY)
            e2 = e2 * e3
            if e1 == e2:
                ret["status"] = "success"
        else:
            ret["message"] = f"Phase not supported for {self.__class__.__name__}"
            logging.error(ret["message"])
        return ret

    def sign(self, message):
        if isinstance(message, str):
            message = message.encode()
        elif not isinstance(message, bytes):
            return {
                "status": "error",
                "message": "Invalid message type. Expected str/bytes"
            }
        ## Randomize u, v and w
        r = Fr.from_random()
        sig = Signature()
        sig.uu.set_object(self.memkey.u * r)
        sig.vv.set_object(self.memkey.v * r)
        sig.ww.set_object(self.memkey.w * r)

        ## Compute signature of knowledge of alpha
        pic, pis = spk_dlog_G1_sign(sig.ww, sig.uu, self.memkey.alpha, message)
        sig.c.set_object(pic)
        sig.s.set_object(pis)
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(self, message, signature):
        if isinstance(message, str):
            message = message.encode()
        elif not isinstance(message, bytes):
            return {
                "status": "error",
                "message": "Invalid message type. Expected str/bytes"
            }
        ret = {"status": "fail"}
        sig = Signature.from_b64(signature)
        ## Verify SPK
        if spk_dlog_G1_verify(sig.ww, sig.uu,
                              sig.c, sig.s, message):
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
        else:
            ret["message"] = "spk_dlog_G1_verify failed"
        return ret


def spk0_sign(y, g, x, i, prods, b_n):
    r = [Fr.from_random() for _ in x]

    ## Compute the challenges according to the relations defined by
    ## the i indexes
    ### Issue https://github.com/IBM/libgroupsig/issues/23
    gr = []
    for j in i:
        gr.append(g[j[1]] * r[j[0]])
    prod = []
    ## Compute the challenge products
    for j in range(4):
        if j < 2:
            pgr = G1.from_object(gr[j])
        else:
            pgr = G2.from_object(gr[j])
        prod.append(pgr)
    prod.append(gr[4] + gr[5])
    prod.append(gr[6] + gr[7])
    ## Compute the hash:
    ## pi->c = Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = g[i[j,2]]^r[i[j,1]]
    blake = hashlib.blake2s()
    blake.update(b_n)
    # Push the y values
    for j in y:
        blake.update(j.to_bytes())
    # Push the base values
    for j in g:
        blake.update(j.to_bytes())
    # Push the indices
    for j in i:
        bi = bytearray([j[0] & 0xFF, (j[0] & 0xFF00) >> 8,
                        j[1] & 0xFF, (j[1] & 0xFF00) >> 8])
        blake.update(bi)
    for j in prod:
        blake.update(j.to_bytes())
    ## Convert the hash to an integer
    pic = Fr.from_hash(blake.digest())
    ## Compute challenge responses
    pis = []
    for idx, j in enumerate(x):
        # si = ri - cxi
        cx = pic * j
        pis.append(r[idx] - cx)
    return pic, pis


def spk0_verify(y, g, i, prods, pic, pis, b_n):
    ## Compute the challenge products -- manually until fixing issue23
    prod = []
    for idx, j in enumerate(y):
        p = j * pic
        if idx == 5:
            idy = idx + 1
        else:
            idy = idx
        gs = g[i[idy][1]] * pis[i[idy][0]]
        prod.append(p + gs)
        if idx > 3:
            idy = idy + 1
            gs = g[i[idy][1]] * pis[i[idy][0]]
            prod[-1] = prod[-1] + gs

    ## if pi is correct, then pi->c must equal:
    ## Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = y[j]^c*g[i[j,2]]^s[i[j,1]]
    # Push the message
    blake = hashlib.blake2s()
    blake.update(b_n)
    # Push the y values
    for j in y:
        blake.update(j.to_bytes())
    # Push the base values
    for j in g:
        blake.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray([j[0] & 0xFF, (j[0] & 0xFF00) >> 8,
                        j[1] & 0xFF, (j[1] & 0xFF00) >> 8])
        blake.update(bytes(bi))
    for j in prod:
        blake.update(j.to_bytes())
    ## Convert the hash to an integer
    c = Fr.from_hash(blake.digest())
    return c == pic


def spk_dlog_G1_sign(G, g, x, s):
    ## Pick random r and compute g^r mod q
    r = Fr.from_random()
    gr = g * r

    ## Make hc = Hash(msg||G||g||g^r)
    h = hashlib.sha256()
    h.update(s)
    h.update(G.to_bytes())
    h.update(g.to_bytes())
    h.update(gr.to_bytes())

    ## Convert the hash to an integer
    c = Fr.from_hash(h.digest())

    # s = r - cx
    s = r - (c * x)
    pis = Fr.from_object(s)
    pic = Fr.from_object(c)
    return pic, pis


def spk_dlog_G1_verify(G, g, pic, pis, message):
    ## If pi is correct, then pi->c must equal Hash(msg||G||g||g^pi->s*g^pi->c)
    ## Compute g^pi->s * g^pi->c
    gs = g * pis
    Gc = G * pic
    gsGc = gs + Gc

    ## Compute the hash
    h = hashlib.sha256()
    h.update(message)
    h.update(G.to_bytes())
    h.update(g.to_bytes())
    h.update(gsGc.to_bytes())

    ## Compare the result with c
    c = Fr.from_hash(h.digest())
    return c == pic
