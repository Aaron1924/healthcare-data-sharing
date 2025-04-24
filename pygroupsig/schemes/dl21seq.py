import hashlib
import hmac
import logging
from typing import Any, Type, TypeVar

import pygroupsig.utils.spk as spk
from pygroupsig.interfaces import Container
from pygroupsig.schemes.dl21 import Group as GroupDL21
from pygroupsig.schemes.dl21 import GroupKey as GroupKeyDL21
from pygroupsig.schemes.dl21 import ManagerKey as ManagerKeyDL21
from pygroupsig.schemes.dl21 import MemberKey as MemberKeyDL21
from pygroupsig.schemes.dl21 import Signature as SignatureDL21
from pygroupsig.utils.mcl import G1, GT, Fr


class MetadataMixin:
    _name = "dl21seq"


T = TypeVar("T", bound=Container)
U = TypeVar("U")


class FromDL21Mixin:
    @classmethod
    def from_dl21(cls: Type[T], o: U) -> T:  # type: ignore
        ret = cls()
        for v in vars(o):
            s_obj = getattr(o, v)
            d_obj = getattr(ret, v)
            d_obj.set_object(s_obj)
        return ret


class GroupKey(FromDL21Mixin, GroupKeyDL21):
    pass


class ManagerKey(FromDL21Mixin, ManagerKeyDL21):
    pass


class MemberKey(FromDL21Mixin, MemberKeyDL21):
    k: str
    kk: str

    def __init__(self) -> None:
        super().__init__()
        self.k = ""
        self.kk = ""


class Signature(FromDL21Mixin, SignatureDL21):
    seq: dict[str, str]

    def __init__(self) -> None:
        super().__init__()
        ## seq(1): Computed as Hash(k',PRF(k,seq3)),
        ## seq(2): Computed as Hash(k',PRF(k,seq3) xor Hash(k, PRF(k,i-1)))
        ## seq(3): Computed as PRF(k,i) -- converted to byte
        self.seq = {}


class Group(GroupDL21[Signature]):
    _logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        super().__init__()
        self.group_key = GroupKey.from_dl21(self.group_key)
        self.manager_key = ManagerKey.from_dl21(self.manager_key)

    ## init, setup, join_mgr, join_mem* are the same as Dl21
    ## join_mem initializes k and k' in the last phase
    def join_mem(  # type: ignore
        self,
        message: dict[str, Any],
        member_key: MemberKey,
    ) -> dict[str, Any]:
        ret = super().join_mem(message, member_key)
        if message["phase"] == 3:
            member_key.k = hashlib.sha256(
                Fr.from_random().to_bytes()
            ).hexdigest()
            member_key.kk = hashlib.sha256(
                Fr.from_random().to_bytes()
            ).hexdigest()
        return ret

    _scheme_signature: Type[Signature] = Signature

    def sign(  # type: ignore
        self,
        message: str,
        member_key: MemberKey,
        scope: str = "def",
        state: int = 0,
    ) -> dict[str, Any]:
        # sign is partially the same
        sig = self._common_sign(message, member_key, scope)
        ## Compute seq3 = PRF(k,state)
        sig.seq["3"] = prf_compute(member_key.k, state)

        ## Compute x_i = PRF(k',state)
        xi = prf_compute(member_key.kk, sig.seq["3"])
        xi_b = bytes.fromhex(xi)

        # seq1 = Hash(x_i)
        sig.seq["1"] = hashlib.sha256(xi_b).hexdigest()

        ## Compute x_{i-1} = PRF(k',PRF(k,state-1))
        ## Recompute n_{i-1} = PRF(k,state-1)
        ni1 = prf_compute(member_key.k, state - 1)
        xi1 = prf_compute(member_key.kk, ni1)
        xi1_b = bytes.fromhex(xi1)
        # seq2 = Hash(x_i \xor x_{i-1})
        _xi = bytearray(a ^ b for a, b in zip(xi_b, xi1_b))
        sig.seq["2"] = hashlib.sha256(_xi).hexdigest()
        return {
            "status": "success",
            "signature": sig.to_b64(),
        }

    def verify(
        self, message: str, signature: str, scope: str = "def"
    ) -> dict[str, Any]:
        message = str(message)
        scope = str(scope)
        ret = {"status": "fail"}
        sig = self._scheme_signature.from_b64(signature)
        ## AA must not be 1 (since we use additive notation for G1,
        ## it must not be 0)
        if not sig.AA.is_zero():
            ## e(AA,ipk) must equal e(A_,g2)
            e1 = GT.pairing(sig.AA, self.group_key.ipk)
            e2 = GT.pairing(sig.A_, self.group_key.g2)
            if e1 == e2:
                ## Recompute hscp
                hc = hashlib.sha256(scope.encode()).digest()
                hscp = G1.from_hash(hc)
                A_d = sig.A_ - sig.d
                y = [sig.nym, A_d, self.group_key.g1]
                g = [hscp, sig.AA, self.group_key.h2, sig.d, self.group_key.h1]
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
                if spk.general_representation_verify(
                    y, g, i, prods, sig.pi, message
                ):
                    ret["status"] = "success"
                else:
                    ret["message"] = "Invalid signature"
                    self._logger.debug("spk.rep_verify failed")
            else:
                ret["message"] = "Invalid signature"
                self._logger.debug("e1 != e2")
        else:
            ret["message"] = "Invalid signature"
            self._logger.debug("AA is zero")
        return ret

    def seqlink(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        key: MemberKey,
        scope: str = "def",
    ) -> dict[str, Any]:
        ret = self.link(message, messages, signatures, key, scope)
        _proof = spk.DiscreteLogProof2.from_b64(ret["proof"])
        ## x[i] = PRF(k',n[i]) = PRF(k',seq3[i])
        for sig_b64 in signatures:
            sig = self._scheme_signature.from_b64(sig_b64)
            _proof.x.append(prf_compute(key.kk, sig.seq["3"]))
        ret["proof"] = _proof.to_b64()
        return ret

    def seqlink_verify(
        self,
        message: str,
        messages: list[str],
        signatures: list[str],
        proof: str,
        scope: str = "def",
    ) -> dict[str, str]:
        _proof2 = spk.DiscreteLogProof2.from_b64(proof)
        _proof = spk.DiscreteLogProof()
        _proof.c.set_object(_proof2.c)
        _proof.s.set_object(_proof2.s)
        ret = self.link_verify(
            message, messages, signatures, _proof.to_b64(), scope
        )
        ## Iterate through sigs and check that
        ## sig[i]->seq1 = Hash(x[i]) and sig[i]->seq2 = Hash(x[i] xor x[i-1])
        for idx, sig_b64 in enumerate(signatures):
            sig = self._scheme_signature.from_b64(sig_b64)
            _hash = hashlib.sha256(bytes.fromhex(_proof2.x[idx])).hexdigest()
            if _hash == sig.seq["1"]:
                if idx > 0:
                    xi1_b = bytes.fromhex(_proof2.x[idx - 1])
                    xi_b = bytes.fromhex(_proof2.x[idx])
                    # seq2 = Hash(x_i \xor x_{i-1})
                    _xi = bytearray(a ^ b for a, b in zip(xi1_b, xi_b))
                    _hash2 = hashlib.sha256(_xi).hexdigest()
                    if _hash2 != sig.seq["2"]:
                        ret["status"] = "fail"
                        ret["message"] = "Invalid signature sequence"
                        self._logger.debug("_hash2 != seq2")
            else:
                ret["status"] = "fail"
                ret["message"] = "Invalid signature sequence"
                self._logger.debug("_hash != seq1")
                break
        return ret


def prf_compute(key: str, state: int | str) -> str:
    return hmac.new(
        bytes.fromhex(key), str(state).encode(), hashlib.sha256
    ).hexdigest()
