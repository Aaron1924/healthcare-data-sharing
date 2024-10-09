from pygroupsig.klap20.scheme import (
    Klap20,
    GroupKey as Klap20GrpKey,
    ManagerKey as Klap20MgrKey,
    MemberKey as Klap20MemKey
)
from pygroupsig.interfaces import (
    KeyInterface,
    SchemeInterface
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
        return self.scheme.join_mgr(self, phase, message)

    def join_mem(self, phase, message=None):
        return self.scheme.join_mem(self, phase, message)


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
