from pygroupsig.klap20.scheme import (
    Klap20,
    GroupKey as Klap20GrpKey,
    ManagerKey as Klap20MgrKey,
    MemberKey as Klap20MemKey,
    Signature as Klap20Signature,
)
from pygroupsig.interfaces import (
    KeyInterface,
    SchemeInterface,
    SignatureInterface,
)


class Scheme(SchemeInterface):
    _SCHEMES = {
        "klap20": Klap20
    }

    def __init__(self, scheme):
        self.scheme = self._get_scheme(scheme)

    def _get_scheme(self, scheme):
        _name = scheme.lower()
        if _name in self._SCHEMES:
            return self._SCHEMES[_name]()
        raise ValueError(f"Unknown scheme: {scheme}")

    def setup(self):
        self.scheme.setup()

    def join_mgr(self, phase, message=None):
        return self.scheme.join_mgr(phase, message)

    def join_mem(self, phase, message=None):
        return self.scheme.join_mem(phase, message)

    def sign(self, message):
        return self.scheme.sign(message)

    def verify(self, message, signature):
        return self.scheme.verify(message, signature)


class Key(KeyInterface):
    _KEYS = {
        "group": {
            "klap20": Klap20GrpKey
        },
        "manager": {
            "klap20": Klap20MgrKey
        },
        "member": {
            "klap20": Klap20MemKey
        }
    }

    def __init__(self, scheme, ktype):
        self.key = self._get_key(scheme, ktype)

    def _get_key(self, scheme, ktype):
        _name = scheme.lower()
        _ktype = ktype.lower()
        if _ktype in self._KEYS:
            if _name in self._KEYS[_ktype]:
                return self._KEYS[_ktype][_name]()
            else:
                raise ValueError(f"Unknown scheme: {scheme}")
        else:
            raise ValueError(f"Unknown key type: {ktype}")


class Signature(SignatureInterface):
    _SIGNATURES = {
        "klap20": Klap20Signature
    }

    def __init__(self, scheme):
        self.signature = self._get_signature(scheme)

    def _get_signature(self, scheme):
        _name = scheme.lower()
        if _name in self._SIGNATURES:
            return self._SIGNATURES[_name]()
        else:
            raise ValueError(f"Unknown scheme: {scheme}")

    def to_b64(self):
        self.signature.to_b64()


# class SPKDLog:
#     def __init__(self):
#         self.c = Fr()
#         self.s = Fr()

#     def to_b64(self):
#         ret = {"c": self.c.to_b64(), "s": self.s.to_b64()}
#         return b64encode(json.dumps(ret)).decode()

#     @classmethod
#     def from_b64(cls, s):
#         ret = cls()
#         dec = b64decode(s.encode())
#         data = json.loads(dec)
#         ret.c.set_from_b64(data["c"])
#         ret.s.set_from_b64(data["s"])
#         return ret


# class SPKRep:
#     def __init__(self):
#         self.c = Fr()
#         self.s = []


# class SPKPairingHomomorphismG2:
#     def __init__(self):
#         self.c = Fr()
#         self.s = G2()


class OpenMixin:
    ...


class OVerifyMixin:
    ...


class RevealTraceClaimCVerifyProveEqPEqVerifyMixin:
    ...


class BlindConvertUnblindMixin:
    ...


class IdentifyLinkLVerifyMixin:
    ...


class SeqlinkSVerifyMixin:
    ...
