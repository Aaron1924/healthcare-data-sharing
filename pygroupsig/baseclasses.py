import json
from base64 import b64encode, b64decode
from pygroupsig.pairings.mcl import Fr


class B64Mixin:
    def to_b64(self):
        meta, var = self.info()
        dump = {}
        for v in var:
            obj = getattr(self, v)
            if isinstance(obj, list):
                dump[v] = [el.to_b64() for el in obj]
            elif isinstance(obj, int):
                dump[v] = obj
            else:
                dump[v] = obj.to_b64()
        data = b64encode(json.dumps(dump).encode()).decode()
        if meta[1] == "signature":
            msg = {"scheme": meta[0], "signature": data}
        else:
            msg = {"scheme": meta[0], "type": meta[1], "key": data}
        return b64encode(json.dumps(msg).encode()).decode()

    def set_b64(self, s):
        data = json.loads(b64decode(s.encode()))
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
            elif isinstance(it[k], int):
                setattr(self, k, it[k])
            else:
                obj.set_b64(it[k])

    @classmethod
    def from_b64(cls, s):
        ret = cls()
        ret.set_b64(s)
        return ret
