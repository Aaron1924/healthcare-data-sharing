from typing import Any

from pygroupsig.interfaces import ContainerInterface, SchemeInterface

SCHEMES: dict[str, Any]

def group(name: str) -> SchemeInterface[ContainerInterface]: ...
def key(
    name: str | None = None,
    ktype: str | None = None,
    b64: str | bytes | None = None,
) -> ContainerInterface: ...
def signature(
    name: str | None = None, b64: str | bytes | None = None
) -> ContainerInterface: ...
