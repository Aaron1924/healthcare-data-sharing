# mypy: disable-error-code="misc"

import importlib
import json
from base64 import b64decode, b64encode
from typing import Any, KeysView, Type, TypeVar

from pygroupsig.interfaces import Container
from pygroupsig.utils.mcl import Fr

_SEQ = 3
_START = 0

T = TypeVar("T", bound="Container")


class ReprMixin:
    def __repr__(self) -> str:
        rep = json.dumps({k: str(v) for k, v in vars(self).items()})
        return f"{self.__class__} {rep}"


class InfoMixin:
    _name: str
    _container_name: str

    def info(self) -> tuple[str, str, KeysView]:
        return self._name, self._container_name, vars(self).keys()


# noinspection PyUnresolvedReferences
class B64Mixin:
    def to_b64(self) -> str:
        scheme_name, container_name, var = self.info()  # type: ignore
        dump: dict[str, Any] = {}
        for v in var:
            obj = getattr(self, v)
            if isinstance(obj, list):
                dump[v] = [el.to_b64() for el in obj]
            elif isinstance(obj, int) or isinstance(obj, dict):
                dump[v] = obj
            elif isinstance(obj, str):
                dump[v] = f"str_{obj}"
            else:
                dump[v] = obj.to_b64()
        data = b64encode(json.dumps(dump).encode()).decode()
        if container_name == "signature":
            msg = {"scheme": scheme_name, "signature": data}
        else:
            msg = {"scheme": scheme_name, "type": container_name, "key": data}
        return b64encode(json.dumps(msg).encode()).decode()

    def set_b64(self, s: str | bytes) -> None:
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        data = json.loads(b64decode(s))
        if "key" in data or "signature" in data:
            if "key" in data:
                d = data["key"]
            else:
                d = data["signature"]
            it = json.loads(b64decode(d.encode()))
        else:
            it = data
        for k, v in it.items():
            obj = getattr(self, k)
            if isinstance(it[k], list):
                obj.extend([Fr.from_b64(el) for el in it[k]])
            elif isinstance(it[k], int) or isinstance(it[k], dict):
                setattr(self, k, it[k])
            elif it[k].startswith("str_"):
                setattr(self, k, it[k].split("_")[1])
            else:
                obj.set_b64(it[k])

    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_b64(s)
        return ret


class JoinMixin:
    @staticmethod
    def join_seq() -> int:
        return _SEQ

    @staticmethod
    def join_start() -> int:
        return _START


class ContainerDict(dict):
    def to_b64(self) -> str:
        exp = {}
        for el, values in self.items():
            exp[el] = [
                f"{v.__class__.__module__}.{v.__class__.__name__}|{v.to_b64()}"
                for v in values
            ]
        return b64encode(json.dumps(exp).encode()).decode()

    def set_b64(self, s: str | bytes) -> None:
        if isinstance(s, str):
            s = s.encode()
        elif not isinstance(s, bytes):
            raise TypeError(f"Invalid {s} type. Expected str/bytes")
        imp = json.loads(b64decode(s))
        for mem_id, data in imp.items():
            values = []
            for el in data:
                c, v = el.split("|")
                path = c.split(".")
                module_name, class_name = ".".join(path[:-1]), path[-1]
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name)
                values.append(cls.from_b64(v))
            self[mem_id] = tuple(values)

    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T:
        ret = cls()
        ret.set_b64(s)
        return ret


GML = ContainerDict
CRL = ContainerDict


class MetadataGroupKeyMixin:
    _container_name = "group"


class MetadataManagerKeyMixin:
    _container_name = "manager"


class MetadataMemberKeyMixin:
    _container_name = "member"


class MetadataBlindKeyMixin:
    _container_name = "blind"


class MetadataSignatureMixin:
    _container_name = "signature"
