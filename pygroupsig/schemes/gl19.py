import hashlib
import logging
import random
import time

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import ContainerInterface, SchemeInterface
from pygroupsig.utils.helpers import B64Mixin, InfoMixin, JoinMixin, ReprMixin
from pygroupsig.utils.mcl import G1, G2, GT, Fr

_NAME = "gl19"


class GroupKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
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


class ManagerKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "manager"

    def __init__(self):
        self.isk = Fr()  # Issuer secret key
        self.csk = Fr()  # Converter secret key
        self.esk = Fr()  # Extractor secret key


class MemberKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
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


class BlindKey(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "blind"

    def __init__(self):
        self.pk = G1()  # Public key. Equals g^sk
        self.sk = Fr()  # Randomly chosen private key

    @classmethod
    def from_random(cls, grpkey):
        ret = cls()
        ret.sk.set_random()
        ret.pk.set_object(grpkey.g * ret.sk)
        return ret

    def public(self):
        return self.pk.to_b64()


class Signature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "signature"

    def __init__(self):
        self.AA = G1()
        self.A_ = G1()
        self.d = G1()
        self.pi = spk.GeneralRepresentationProof()
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


class BlindSignature(B64Mixin, InfoMixin, ReprMixin, ContainerInterface):
    _NAME = _NAME
    _CTYPE = "blind_signature"

    def __init__(self):
        self.nym1 = G1()
        self.nym2 = G1()
        self.nym3 = G1()
        self.c1 = G1()
        self.c2 = G1()


class GL19(JoinMixin, ReprMixin, SchemeInterface):
    LIFETIME = 60 * 60 * 24 * 14  # two weeks
    # TODO: add lifetime setter
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self.grpkey = GroupKey()
        self.mgrkey = ManagerKey()

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

        ## I'll simplify this scheme, instead of using multiple setup calls,
        ## the first call will also generate the converter key
        ## Generate the Converter's private key
        self.mgrkey.csk.set_random()

        ## Add the Converter's public key to the group key
        self.grpkey.cpk.set_object(self.grpkey.g * self.mgrkey.csk)

        ## Generate the Extractor's private key
        self.mgrkey.esk.set_random()

        ## Add the Extractor's public key to the group key
        self.grpkey.epk.set_object(self.grpkey.g * self.mgrkey.esk)

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
                ## Compute credential from H and pi_H. Verify the proof
                n = G1.from_b64(message["n"])
                H = G1.from_b64(message["H"])
                proof = spk.DiscreteLogProof.from_b64(message["pi"])

                if spk.discrete_log_verify(
                    H, self.grpkey.h1, proof, n.to_bytes()
                ):
                    ## Pick x and s at random from Z*_p
                    x = Fr.from_random()
                    s = Fr.from_random()

                    life = str(int(time.time() + self.LIFETIME))
                    h = hashlib.sha256(life.encode())
                    ## Modification w.r.t. the GL19 paper: we add a maximum lifetime
                    ## for member credentials. This is done by adding a second message
                    ## to be signed in the BBS+ signatures. This message will then be
                    ## "revealed" (i.e., shared in cleartext) in the SPK computed for
                    ## signing
                    d = Fr.from_hash(h.digest())

                    ## Set A = (H+h_2*s+h3*d+g_1)*((isk+x)**-1)
                    h2s = self.grpkey.h2 * s
                    h3d = self.grpkey.h3 * d
                    A = (H + h2s + h3d + self.grpkey.g1) * ~(
                        self.mgrkey.isk + x
                    )

                    ## Mout = (A,x,s,l)
                    ret["status"] = "success"
                    ret["A"] = A.to_b64()
                    ret["x"] = x.to_b64()
                    ret["s"] = s.to_b64()
                    ret["l"] = life
                    ret["phase"] = phase + 1
                else:
                    ret["status"] = "fail"
                    ret["message"] = "Invalid message content"
                    self._logger.debug("spk.dlog_G1_verify failed")
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
            ## Parse n and compute (Y,\pi_Y)
            n = G1.from_b64(message["n"])

            ## Compute member's secret key y at random
            key.y.set_random()

            ## Compute the member's public key
            key.H.set_object(self.grpkey.h1 * key.y)

            ## Compute the SPK
            proof = spk.discrete_log_sign(
                key.H, self.grpkey.h1, key.y, n.to_bytes()
            )

            ## Build the output message
            ret["status"] = "success"
            ret["n"] = n.to_b64()
            ret["H"] = key.H.to_b64()
            ret["pi"] = proof.to_b64()
            ret["phase"] = phase + 1
        elif phase == 3:
            ## Check correctness of computation and update memkey

            # Min = (A,x,s,l)
            key.A.set_b64(message["A"])
            key.x.set_b64(message["x"])
            key.s.set_b64(message["s"])
            key.l = int(message["l"])

            ## Recompute h2s from s
            key.h2s.set_object(self.grpkey.h2 * key.s)

            ## Recompute d and h3d from l
            h = hashlib.sha256(str(key.l).encode())
            key.d.set_hash(h.digest())
            key.h3d.set_object(self.grpkey.h3 * key.d)

            ## Check correctness
            # A must not be 1 (since we use additive notation for G1,
            # it must not be 0)
            if not key.A.is_zero():
                e1 = (GT.pairing(key.A, self.grpkey.g2)) ** key.x
                e2 = GT.pairing(key.A, self.grpkey.ipk)
                e4 = e1 * e2
                aux = key.H + key.h2s + key.h3d + self.grpkey.g1
                e3 = GT.pairing(aux, self.grpkey.g2)
                if e4 == e3:
                    ret["status"] = "success"
                else:
                    ret["status"] = "fail"
                    ret["message"] = "Invalid message content"
                    self._logger.debug("e4 != e3")
            else:
                ret["status"] = "fail"
                ret["message"] = "Invalid message content"
                self._logger.debug("A is zero")
        else:
            ret["message"] = (
                f"Phase not supported for {self.__class__.__name__}"
            )
            self._logger.error(ret["message"])
        return ret

    def sign(self, message, key):
        message = str(message)
        # alpha, r1, r2 \in_R Z_p
        alpha = Fr.from_random()
        r1 = Fr.from_random()
        r2 = Fr.from_random()

        # nym1 = g1*alpha
        sig = Signature()
        sig.nym1.set_object(self.grpkey.g * alpha)

        # nym2 = cpk*alpha+h*y
        sig.nym2.set_object((self.grpkey.cpk * alpha) + (self.grpkey.h * key.y))

        ## Add extra encryption of h^y with epk
        alpha2 = Fr.from_random()

        # ehy1 = g*alpha2
        sig.ehy1.set_object(self.grpkey.g * alpha2)

        # ehy2 = epk*alpha2+h*y
        sig.ehy2.set_object(
            (self.grpkey.epk * alpha2) + (self.grpkey.h * key.y)
        )

        # AA = A*r1
        sig.AA.set_object(key.A * r1)

        ## Good thing we precomputed much of this...
        # aux = (g1+h1*y+h2*s+h3*d)*r1
        aux = (self.grpkey.g1 + key.H + key.h2s + key.h3d) * r1
        # A_ = AA^{-x}(g1+h*y+h2*s+h3*d)*r1
        sig.A_.set_object(sig.AA * -key.x + aux)

        # d = (g1+h1*y+h2*s+h3*d)*r1+h2*-r2
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
        proof = spk.general_representation_sign(
            y, g, x, i, prods, f"{sig.expiration}|{message}"
        )
        sig.pi.c.set_object(proof.c)
        sig.pi.s.extend(proof.s)

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

        h = hashlib.sha256(str(sig.expiration).encode())
        expiration = Fr.from_hash(h.digest())
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
        if spk.general_representation_verify(
            y, g, i, prods, sig.pi, f"{sig.expiration}|{message}"
        ):
            ret["status"] = "success"
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("spk.rep_verify failed")
        return ret

    def blind(self, message, signature, blind_key=None):
        if blind_key is None:
            blind_key = BlindKey.from_random(self.grpkey)
        message = str(message)
        sig = Signature.from_b64(signature)

        ## Pick alpha, beta, gamma at random from Z^*_p
        alpha = Fr.from_random()
        beta = Fr.from_random()
        gamma = Fr.from_random()

        ## Rerandomize the pseudonym encryption under the cpk and
        ## add an encryption layer for the pseudonym under the bpk
        bsig = BlindSignature()
        bsig.nym1.set_object(sig.nym1 + (self.grpkey.g * beta))
        bsig.nym2.set_object(self.grpkey.g * alpha)
        bsig.nym3.set_object(
            sig.nym2 + (self.grpkey.cpk * beta) + (blind_key.pk * alpha)
        )

        ##  Encrypt the (hash of the) message
        h = hashlib.sha256()
        h.update(message.encode())
        c = G1.from_hash(h.digest())
        bsig.c1.set_object(self.grpkey.g * gamma)
        bsig.c2.set_object(c + (blind_key.pk * gamma))
        return {
            "status": "success",
            "blind_signature": bsig.to_b64(),
            "blind_key": blind_key.to_b64(),
        }

    def convert(self, blind_signatures, blind_key_public):
        r = Fr.from_random()
        neg_csk = -self.mgrkey.csk
        converted_signatures = []
        pk = G1.from_b64(blind_key_public)
        for bsig_b64 in blind_signatures:
            bsig = BlindSignature.from_b64(bsig_b64)
            r1 = Fr.from_random()
            r2 = Fr.from_random()
            ## Decrypt nym and raise to r
            cnym1p = bsig.nym2 * r
            cnym2p = ((bsig.nym1 * neg_csk) + bsig.nym3) * r

            ## Re-randomize nym
            csig = BlindSignature()
            csig.nym1.set_object(cnym1p + (self.grpkey.g * r1))
            csig.nym2.set_object(cnym2p + (pk * r1))
            ## nym3 is empty (default value 0)

            ## Re-randomize ciphertext
            csig.c1.set_object(bsig.c1 + (self.grpkey.g * r2))
            csig.c2.set_object(bsig.c2 + (pk * r2))
            converted_signatures.append(csig.to_b64())
        durstenfeld_perm(converted_signatures)
        return {
            "status": "success",
            "converted_signatures": converted_signatures,
        }

    def unblind(self, converted_signature, blind_key):
        csig = BlindSignature.from_b64(converted_signature)
        ## Decrypt the pseudonym with the blinding private key
        aux_zn = -blind_key.sk
        id_ = (csig.nym1 * aux_zn) + csig.nym2

        ## Decrypt the (hashed) message with the blinding private key
        aux_G1 = csig.c1 * aux_zn
        aux_G1 = csig.c2 + aux_G1

        ## Update the received message with the string representation of aux_G1
        ## Really required? It has no use
        return {
            "status": "success",
            "nym": id_.to_b64(),
        }


def durstenfeld_perm(input_list):
    """
    Uses Durstenfeld variant of the Fisher-Yates in place permutation
    algorithm to output a random permutation of the given array.

    See https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle#The_modern_algorithm
    for a definition of the algorithm.
    """
    for i in range(len(input_list) - 2):
        j = random.randint(i, len(input_list))
        tmp = input_list[i]
        input_list[i] = input_list[j]
        input_list[j] = tmp
