from socks5server.enums import AuthMethod
from socks5server.packets.base import BasePacket


class ChooseAuthMethod(BasePacket):
    __slots__ = ("method",)

    def __init__(self, method: AuthMethod) -> None:
        self.method = method

    def write(self) -> bytes:
        return self.VERSION + bytes([self.method.value])