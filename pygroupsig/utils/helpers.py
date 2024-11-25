import importlib
import json
from base64 import b64decode, b64encode

from pygroupsig.utils.mcl import Fr

_SEQ = 3
_START = 0


class ReprMixin:
    def __repr__(self):
        rep = json.dumps({k: str(v) for k, v in vars(self).items()})
        return f"{self.__class__} {rep}"


class InfoMixin:
    def info(self):
        return (self._NAME, self._CTYPE), vars(self).keys()


class B64Mixin:
    def to_b64(self):
        meta, var = self.info()
        dump = {}
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
        if meta[1] == "signature":
            msg = {"scheme": meta[0], "signature": data}
        else:
            msg = {"scheme": meta[0], "type": meta[1], "key": data}
        return b64encode(json.dumps(msg).encode()).decode()

    def set_b64(self, s):
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
    def from_b64(cls, s):
        ret = cls()
        ret.set_b64(s)
        return ret


class InfoLMixin:
    def info(self):
        return self._NAME, self._CTYPE


class JoinMixin:
    def join_seq(self):
        return _SEQ

    def join_start(self):
        return _START


class ContainerDict(dict):
    def to_b64(self):
        exp = {}
        for el, values in self.items():
            exp[el] = [
                f"{v.__class__.__module__}.{v.__class__.__name__}|{v.to_b64()}"
                for v in values
            ]
        return b64encode(json.dumps(exp).encode())

    def set_b64(self, s):
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
    def from_b64(cls, s):
        ret = cls()
        ret.set_b64(s)
        return ret


GML = ContainerDict
CRL = ContainerDict
