from enum import IntEnum, Enum, auto


class AuthMethod(IntEnum):
    NO_AUTH = 0x00
    GSSAPI = 0x01
    PASSWORD = 0x02
    INVALID = 0xFF


class AddressType(IntEnum):
    IPV4 = 0x01
    DOMAIN = 0x03
    IPV6 = 0x04


class CommandType(IntEnum):
    CONNECT = 0x01
    BIND = 0x02
    UDP_ASSOCIATE = 0x03


class ReplyStatus(IntEnum):
    SUCCESS = 0x00
    SERVER_FAILURE = 0x01
    NOT_ALLOWED = 0x02
    NETWORK_UNREACHABLE = 0x03
    HOST_UNREACHABLE = 0x04
    CONNECTION_REFUSED = 0x05
    TTL_EXPIRED = 0x06
    COMMAND_NOT_SUPPORTED = 0x07
    ADDRESS_NOT_SUPPORTED = 0x08


class ClientEventType(Enum):
    CONNECT = auto()
    DISCONNECT = auto()
    DATA = auto()
    DATA_MODIFY = auto()
    DEST_CONNECT = auto()


class DataModify(Enum):
    DONT_SEND = auto()
