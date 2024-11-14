import hashlib

from pygroupsig.pairings.mcl import G1, G2, GT, Fr


def sign(y, g, x, i, prods, b_n):
    r = [Fr.from_random() for _ in x]

    ## Compute the challenges according to the relations defined by
    ## the i indexes
    ### Issue https://github.com/IBM/libgroupsig/issues/23
    gr = [g[j[1]] * r[j[0]] for j in i]

    ## Compute the challenge products
    prod = []
    for j in range(4):
        # TODO: remove from_object
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
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    ## Convert the hash to an integer
    pic = Fr.from_hash(h.digest())

    ## Compute challenge responses
    pis = []
    for idx, j in enumerate(x):
        # si = ri - cxi
        cx = pic * j
        pis.append(r[idx] - cx)
    return pic, pis


def verify(y, g, i, prods, pic, pis, b_n):
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
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    ## Convert the hash to an integer
    c = Fr.from_hash(h.digest())
    return c == pic


def rep_sign(y, g, x, i, prods, b_n):
    r = [Fr.from_random() for _ in x]

    ## Compute the challenges according to the relations defined by
    ## the i indexes
    gr = [g[j[1]] * r[j[0]] for j in i]

    ## Compute the challenge products
    prod = []
    idx = 0
    for j in range(len(y)):
        pgr = G1.from_object(gr[idx])
        prod.append(pgr)
        idx += 1
        if prods[j] > 1:
            ## We use prods to specify how the i indexes are 'assigned' per
            ## random 'challenge'
            for k in range(prods[j] - 1):
                prod[j] = prod[j] + gr[idx]
                idx += 1
    # print("rep_sign: ", prod)

    ## Compute the hash:
    ## pi->c = Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = g[i[j,2]]^r[i[j,1]]
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    # print("bn sign: ", b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    # print(h.hexdigest())
    ## Convert the hash to an integer
    pic = Fr.from_hash(h.digest())

    ## Compute challenge responses
    pis = []
    for idx, j in enumerate(x):
        # si = ri - cxi
        cx = pic * j
        pis.append(r[idx] - cx)
    return pic, pis


def rep_verify(y, g, i, prods, pic, pis, b_n):
    ## Compute the challenge products -- manually until fixing issue23
    prod = []
    idx = 0
    for j in range(len(y)):
        prod.append(y[j] * pic)
        if prods[j] >= 1:
            ## We use prods to specify how the i indexes are 'assigned' per
            ## random 'challenge'
            for k in range(prods[j]):
                gs = g[i[idx][1]] * pis[i[idx][0]]
                prod[j] = prod[j] + gs
                idx += 1
    # print("rep_verify: ", prod)

    ## if pi is correct, then pi->c must equal:
    ## Hash(msg, y[1..ny], g[1..ng], i[1,1], i[1,2] .. i[ni,1], i[ni,2], prod[1..ny])
    ## where prod[j] = y[j]^c*g[i[j,2]]^s[i[j,1]]
    # Push the message
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    # print("bn ver: ", b_n)

    # Push the y values
    for j in y:
        h.update(j.to_bytes())

    # Push the base values
    for j in g:
        h.update(j.to_bytes())

    # Push the indices
    for j in i:
        bi = bytearray(
            [
                j[0] & 0xFF,
                (j[0] & 0xFF00) >> 8,
                j[1] & 0xFF,
                (j[1] & 0xFF00) >> 8,
            ]
        )
        h.update(bi)

    # Push the products
    for j in prod:
        h.update(j.to_bytes())

    # print(h.hexdigest())
    ## Convert the hash to an integer
    c = Fr.from_hash(h.digest())
    return c == pic


def dlog_G1_sign(G, g, x, b_n):
    ## Pick random r and compute g^r mod q
    r = Fr.from_random()
    gr = g * r

    ## Make hc = Hash(msg||G||g||g^r)
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
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


def dlog_G1_verify(G, g, pic, pis, b_n):
    ## If pi is correct, then pi->c must equal Hash(msg||G||g||g^pi->s*g^pi->c)
    ## Compute g^pi->s * g^pi->c
    gs = g * pis
    Gc = G * pic
    gsGc = gs + Gc

    ## Compute the hash
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(G.to_bytes())
    h.update(g.to_bytes())
    h.update(gsGc.to_bytes())

    ## Compare the result with c
    c = Fr.from_hash(h.digest())
    return c == pic


def pairing_homomorphism_G2_sign(g, G, xx, b_n):
    ## Pick random R from G2
    rr = G2.from_random()
    ## Compute the map
    R = GT.pairing(g, rr)

    ## Make hc = Hash(msg||g||G||R)
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(g.to_bytes())
    h.update(G.to_bytes())
    h.update(R.to_bytes())

    ## Convert the hash to an integer
    c = Fr.from_hash(h.digest())

    # ss = rr+xx*c
    ss = rr + (xx * c)
    # pi = (s,c)
    pic = Fr.from_object(c)
    pis = G2.from_object(ss)
    return pic, pis


def pairing_homomorphism_G2_verify(g, G, pic, pis, b_n):
    ## If pi is correct, then pi->c equals Hash(msg||g||G||e(g,pi->ss)/G**pi->c)
    ## Compute e(g,pi->ss)/G**pi->c
    Gc = G**pic
    R = GT.pairing(g, pis) / Gc

    # Compute the hash
    h = hashlib.sha256()
    if isinstance(b_n, str):
        b_n = b_n.encode()
    h.update(b_n)
    h.update(g.to_bytes())
    h.update(G.to_bytes())
    h.update(R.to_bytes())

    ## Compare the result with c
    c = Fr.from_hash(h.digest())
    return c == pic


def sign1(xx, g1, g2, e1, e2, b_n):
    # RR1 = e(g1,rr), RR2 = e(g2,rr)
    rr = G2.from_random()
    RR1 = GT.pairing(g1, rr)
    RR2 = GT.pairing(g2, rr)

    # c = Hash(g1,g2,e1,e2,RR1,RR2,msg)
    h = hashlib.sha256()
    h.update(g1.to_bytes())
    h.update(g2.to_bytes())
    h.update(e1.to_bytes())
    h.update(e2.to_bytes())
    h.update(RR1.to_bytes())
    h.update(RR2.to_bytes())

    c = Fr.from_hash(h.digest())
    # s = rr + xx*c
    s = rr + (xx * c)

    pic = Fr.from_object(c)
    pis = G2.from_object(s)
    return pic, pis


def verify1(pic, pis, g1, g2, e1, e2, b_n):
    # RR1 = e(g1,pi->s)/e1**pi->c
    RR1 = GT.pairing(g1, pis) / (e1**pic)
    # RR2 = e(g2,pi->s)/e2**pi->c
    RR2 = GT.pairing(g2, pis) / (e2**pic)
    h = hashlib.sha256()
    h.update(g1.to_bytes())
    h.update(g2.to_bytes())
    h.update(e1.to_bytes())
    h.update(e2.to_bytes())
    h.update(RR1.to_bytes())
    h.update(RR2.to_bytes())

    c = Fr.from_hash(h.digest())
    return pic == c
