import socket

from socks5server.enums import AuthMethod, ReplyStatus, AddressType
from socks5server.packets.base import BasePacket


class CommandReply(BasePacket):
    __slots__ = ("status", "address_type", "address", "port",)

    def __init__(self, status: ReplyStatus, address_type: AddressType, address: str, port: int) -> None:
        self.status = status
        self.address_type = address_type
        self.address = address
        self.port = port

    def write(self) -> bytes:
        address = None
        if self.address_type is AddressType.IPV4:
            address = socket.inet_aton(self.address)
        elif self.address_type is AddressType.IPV6:
            address = socket.inet_pton(socket.AF_INET6, self.address)
        elif self.address_type is AddressType.DOMAIN:
            address = self.address.encode("utf8")
            address = bytes([len(address)]) + address
        else:
            raise RuntimeError("Unreachable")

        return (
                self.VERSION
                + bytes([self.status.value, 0, self.address_type.value])
                + address
                + self.port.to_bytes(2, "big")
        )