from abc import abstractmethod, ABC


class BasePacket(ABC):
    VERSION = b"\x05"

    @abstractmethod
    def write(self) -> bytes:
        ...