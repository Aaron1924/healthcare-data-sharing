from abc import ABCMeta, abstractmethod
from typing import Generic, Type, TypeVar

T = TypeVar("T")
C = TypeVar("C", bound="ContainerInterface")
MemberKey = TypeVar("MemberKey", bound="ContainerInterface")

class SchemeInterface(Generic[MemberKey], metaclass=ABCMeta):
    grpkey: ContainerInterface
    mgrkey: ContainerInterface
    @abstractmethod
    def setup(self) -> None: ...
    @abstractmethod
    def join_mgr(
        self, message: dict[str, str] | None = None
    ) -> dict[str, str]: ...
    @abstractmethod
    def join_mem(
        self, message: dict[str, str], key: MemberKey
    ) -> dict[str, str]: ...
    @abstractmethod
    def sign(self, message: str, key: MemberKey) -> dict[str, str]: ...
    @abstractmethod
    def verify(self, message: str, signature: str) -> dict[str, str]: ...

class ContainerInterface(metaclass=ABCMeta):
    _NAME: str
    _CTYPE: str
    @abstractmethod
    def to_b64(self) -> str: ...
    @abstractmethod
    def set_b64(self, s: str | bytes) -> None: ...
    @classmethod
    def from_b64(cls: Type[T], s: str | bytes) -> T: ...
    @abstractmethod
    def info(self) -> tuple[tuple[str], list[str]]: ...
