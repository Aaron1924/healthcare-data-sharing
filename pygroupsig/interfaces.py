from abc import ABCMeta, abstractmethod


class SchemeInterface(metaclass=ABCMeta):
    @abstractmethod
    def setup(self):
        """
        Create a specific scheme instance, setting the group
        and manager keys, and the GML (if scheme implements it).
        """

    @abstractmethod
    def join_mem(self, phase, message=None):
        """
        Functions of this type are executed by entities who want to be
        included in a group. They run in coordination with the equivalent
        functions run by managers (join_mgr).
        """

    @abstractmethod
    def join_mgr(self, phase, message=None):
        """
        Functions of this type are executed by group managers. From a
        partial member key, as produced by the corresponding join_mem
        function, these functions create a complete member key, adding the
        new member to any necessary component (e.g. GMLs).
        """

    @abstractmethod
    def sign(self, message):
        """
        Type of functions for signing messages.
        """

    @abstractmethod
    def verify(self, message, signature):
        """
        Type of functions for verifying group signatures.
        """


class KeyInterface(metaclass=ABCMeta):
    # @abstractmethod
    # def to_b64(self):
    #     ...

    # @abstractmethod
    # def from_b64(self):
    #     ,,,

    # @abstractmethod
    # def to_string(self):
    #     ...
    ...


class SignatureInterface(metaclass=ABCMeta):
    # @abstractmethod
    # def to_b64(self):
    #     ...

    # @abstractmethod
    # def from_b64(self):
    #     ,,,

    # @abstractmethod
    # def to_string(self):
    #     ...
    ...
