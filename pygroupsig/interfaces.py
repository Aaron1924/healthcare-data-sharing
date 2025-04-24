from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Generic, KeysView, Type, TypeVar


class Container(ABC):
    _scheme_name: str
    _container_type: str

    @abstractmethod
    def info(self) -> tuple[str, str, KeysView]:
        """
        Listing of internal properties
        """

    @abstractmethod
    def to_b64(self) -> str:
        """
        Export internal properties to base64
        """

    @abstractmethod
    def set_b64(self, s: str | bytes) -> None:
        """
        Import base64 to internal properties
        """

    @classmethod
    @abstractmethod
    def from_b64(cls: Type["Container"], s: str | bytes) -> "Container":
        """
        Create new object from base64
        """


GroupKeyT = TypeVar("GroupKeyT", bound="Container")
ManagerKeyT = TypeVar("ManagerKeyT", bound="Container")
MemberKeyT = TypeVar("MemberKeyT", bound="Container")


class Scheme(Generic[GroupKeyT, ManagerKeyT, MemberKeyT], ABC):
    _scheme_name: str
    group_key: GroupKeyT
    manager_key: ManagerKeyT
    _logger: Logger

    @abstractmethod
    def setup(self) -> None:
        """
        Create a specific scheme instance, setting the group
        and manager keys, and the GML (if scheme implements it).
        """

    @staticmethod
    @abstractmethod
    def join_start() -> int:
        """
        Functions returning who sends the first message in the join protocol, i.e. 0=manager, 1=member.
        """

    @staticmethod
    @abstractmethod
    def join_seq() -> int:
        """
        Functions returning the number of messages to be exchanged in the join protocol.
        """

    @abstractmethod
    def join_mgr(self, message: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Functions of this type are executed by group managers. From a
        partial member key, as produced by the corresponding join_mem
        function, these functions create a complete member key, adding the
        new member to any necessary component (e.g. GMLs).
        """

    @abstractmethod
    def join_mem(
        self, message: dict[str, Any], member_key: MemberKeyT
    ) -> dict[str, Any]:
        """
        Functions of this type are executed by entities who want to be
        included in a group. They run in coordination with the equivalent
        functions run by managers (join_mgr).
        """

    @abstractmethod
    def sign(self, message: str, member_key: MemberKeyT) -> dict[str, Any]:
        """
        Type of functions for signing messages.
        """

    @abstractmethod
    def verify(self, message: str, signature: str) -> dict[str, Any]:
        """
        Type of functions for verifying group signatures.
        """
