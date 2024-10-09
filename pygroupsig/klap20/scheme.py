import json
import hashlib
from pygroupsig.pairings.mcl import Fr, G1, G2, GT
from pygroupsig.interfaces import SchemeInterface, KeyInterface


class GroupKey(KeyInterface):
    g = G1()
    gg = G2()
    XX = G2()
    YY = G2()
    ZZ0 = G2()
    ZZ1 = G2()


class ManagerKey(KeyInterface):
    x = Fr()
    y = Fr()
    z0 = Fr()
    z1 = Fr()


class MemberKey(KeyInterface):
    alpha = Fr()
    u = G1()
    v = G1()
    w = G1()


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
        self.grpkey.XX.set_from_object(self.grpkey.gg * self.mgrkey.x)
        self.grpkey.YY.set_from_object(self.grpkey.gg * self.mgrkey.y)

        ## Initialize the Opener's key
        self.mgrkey.z0.set_random()
        self.mgrkey.z1.set_random()

        ## Finalize the group key with the Opener's public key
        self.grpkey.ZZ0.set_from_object(self.grpkey.gg * self.mgrkey.z0)
        self.grpkey.ZZ1.set_from_object(self.grpkey.gg * self.mgrkey.z1)

    def join_mgr(self, phase, message=None):
        if phase == 0:
            ## Send a random element to the member
            n = G1()
            n.set_random()
            return {"n": n.to_b64()}
        elif phase == 2:
            if not isinstance(message, dict):
                raise TypeError("Invalid message type. Expected dict")
            ## Import the (n,f,w,SSO,SS1,ff0,ff1,pic,pis) ad hoc message
            n = G1.from_b64(message["n"])
            f = G1.from_b64(message["f"])
            w = G1.from_b64(message["w"])
            SS0 = G2.from_b64(message["SS0"])
            SS1 = G2.from_b64(message["SS1"])
            ff0 = G2.from_b64(message["ff0"])
            ff1 = G2.from_b64(message["ff1"])
            pic = Fr.from_b64(message["pic"])
            _pis = json.loads(message["pis"])
            pis = []
            for p in _pis:
                el = Fr.from_b64(p.encode())
                pis.append(el)
            b_n = n.to_bytes()
            ## Check the SPK -- this will change with issue23
            ## Compute the SPK for sk -- this will be replaced in issue23
            # u = Hash(f)
            b_f = f.to_bytes()
            h = hashlib.blake2s(b_f).digest()
            u = G1()
            breakpoint()
            u.set_hash(h)
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
            if spk0_verify(y, g, i, prods, pic, pis, b_n):
                w = w * self.mgrkey.y
                u = u * self.mgrkey.x
                v = u + w
                # Add the tuple (i,SS0,SS1,ff0,ff1,tau) to the GML
                tau = GT.pairing(f, self.grpkey.gg)
                # Currently, KLAP20 identities are just uint64_t's
                mem_id = hashlib.sha256(
                    SS0.to_bytes() + SS1.to_bytes() +
                    ff0.to_bytes() + ff1.to_bytes() +
                    tau.to_bytes()
                ).hexdigest()
                self.gml[mem_id] = (SS0, SS1, ff0, ff1, tau)
                return {"v": v.to_b64()}
        else:
            raise NotImplementedError(
                f"Phase not supported for {self.__class__.__name__}"
            )

    def join_mem(self, phase, message):
        if phase == 1:
            ## The manager sends a random element in G1
            n = G1.from_b64(message["n"])
            b_n = n.to_bytes()

            ## Compute secret alpha, s0 and s1
            self.memkey = MemberKey()
            self.memkey.alpha.set_random()
            s0 = Fr()
            s0.set_random()
            s1 = Fr()
            s1.set_random()

            # f = g^alpha
            f = G1.from_object(self.grpkey.g * self.memkey.alpha)

            # u = Hash(f)
            # TODO, benckmark blake2s vs blake2b speed depending of the CPU
            bf = f.to_bytes()
            h = hashlib.blake2s(bf).digest()
            self.memkey.u.set_from_bytes(h)

            # w = u^alpha
            self.memkey.w.from_object(self.memkey.u * self.memkey.alpha)

            # SS0 = gg^s0
            SS0 = G2()
            SS0.from_object(self.grpkey.gg * s0)

            # SS1 = gg^s1
            SS1 = G2()
            SS1.from_object(self.grpkey.gg * s1)

            # ff0 = gg^alpha*ZZ0^s0
            ggalpha = G2()
            ggalpha.from_object(self.grpkey.gg * self.memkey.alpha)
            ZZ0s0 = G2()
            ZZ0s0.from_object(self.grpkey.ZZ0 * s0)
            ff0 = G2()
            ff0.from_object(ggalpha + ZZ0s0)

            # ff1 = gg^alpha*ZZ1^s1
            ZZ1s1 = G2()
            ZZ1s1.from_object(self.grpkey.ZZ1 * s1)
            ff1 = G2()
            ff1.from_object(ggalpha + ZZ1s1)

            # tau = e(f,gg)
            tau = GT()
            tau.pairing(f, self.grpkey.gg)

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
            pic, pis = spk0_sign(y, g, x, i, prods, b_n)
            ## Need to send (n, f, w, SS0, SS1, ff0, ff1, pi): prepare ad hoc message
            return {
                "n": n.to_b64(),
                "f": f.to_b64(),
                "w": self.memkey.w.to_b64(),
                "SS0": SS0.to_b64(),
                "SS1": SS1.to_b64(),
                "ff0": ff0.to_b64(),
                "ff1": ff1.to_b64(),
                "pic": pic.to_b64(),
                "pis": json.dumps([p.to_b64().decode() for p in pis]),
            }
        elif phase == 3:
            # Min = v
            v = G1()
            v.from_b64(message["v"])
            # Check correctness: e(v,gg) = e(u,XX)e(w,YY)
            e1 = GT()
            e1.pairing(self.memkey.v, self.grpkey.gg)
            e2 = GT()
            e2.pairing(self.memkey.u, self.grpkey.XX)
            e3 = GT()
            e3.pairing(self.memkey.w, self.grpkey.YY)
            e2 = e2 * e3
            if e1.cmp(e2):
                return True
        else:
            raise NotImplementedError(
                f"Phase not supported for {self.__class__.__name__}"
            )

    def sign(self):
        pass

    def verify(self):
        pass


def spk0_sign(y, g, x, i, prods, b_n):
    r = []
    for j in x:
        rj = Fr()
        rj.set_random()
        r.append(rj)
    # Compute the challenges according to the relations defined by
    # the i indexes
    # Issue https://github.com/IBM/libgroupsig/issues/23
    gr = []
    for j in i:
        gr.append(g[j[1]] * r[j[0]])
    prod = []
    # Compute the challenge products
    for j in range(6):
        if j < 2:
            pgr = G1()
        else:
            pgr = G2()
        if j < 4:
            pgr.from_object(gr[j])
        # is this code unreachable? https://gitlab.gicp.es/spirs/libgroupsig/-/blob/master/src/groupsig/klap20/spk.c#L114
        prod.append(pgr)
    prod[4] = gr[4] + gr[5]
    prod[5] = gr[6] + gr[7]
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
    pic = Fr()
    pic.set_hash(blake.digest())
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
        blake.update(bi)
    for j in prod:
        blake.update(j.to_bytes())
    ## Convert the hash to an integer
    c = Fr()
    c.set_hash(blake.digest())
    return c == pic
