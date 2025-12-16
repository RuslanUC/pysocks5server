from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING

from socks5server.enums import AuthMethod, AddressType, CommandType, ReplyStatus, ClientEventType
from socks5server.exceptions import Disconnection

from socks5server.packets.choose_auth_method import ChooseAuthMethod
from socks5server.packets.command_reply import CommandReply
from socks5server.relay import ClientDstRelay

if TYPE_CHECKING:
    from socks5server.server import SocksServer


_SUPPORTED_COMMANDS = {CommandType.CONNECT}
_INVALID_COMMAND = CommandReply(
    status=ReplyStatus.COMMAND_NOT_SUPPORTED,
    address_type=AddressType.IPV4,
    address="0.0.0.0",
    port=0,
).write()
_INVALID_ADDRESS = CommandReply(
    status=ReplyStatus.ADDRESS_NOT_SUPPORTED,
    address_type=AddressType.IPV4,
    address="0.0.0.0",
    port=0,
).write()


class Socks5Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server: SocksServer):
        self._reader = reader
        self._writer = writer
        self._server = server

        self._dst_writer: asyncio.StreamWriter | None = None
        self._dst_server: asyncio.StreamReader | None = None

        self._bind_server = None

    def __repr__(self) -> str:
        addr, port = self._writer.get_extra_info("peername")
        return f"Socks5Client(address={addr!r}, port={port!r})"

    async def handle(self):
        await self.authenticate()
        await self.handle_connection_request()

    async def authenticate(self):
        auth_methods_len, = await self._reader.read(1)
        method = self._server.choose_auth_method(await self._reader.readexactly(auth_methods_len))

        if method is None:
            self._writer.write(ChooseAuthMethod(AuthMethod.INVALID).write())
            await self._writer.drain()
            raise Disconnection

        method_type, auth_method = method

        self._writer.write(ChooseAuthMethod(method_type).write())
        await self._writer.drain()

        if not await auth_method.authenticate(self._reader, self._writer):
            raise Disconnection

    async def _read_address(self) -> str | None:
        addr_type, = await self._reader.read(1)
        if addr_type not in AddressType._value2member_map_:
            return None

        addr_type = AddressType(addr_type)

        if addr_type is AddressType.IPV4:
            addr = await self._reader.read(4)
            return socket.inet_ntoa(addr)
        elif addr_type is AddressType.DOMAIN:
            ln, = await self._reader.read(1)
            domain = await self._reader.read(ln)
            return domain.decode("utf8")
        elif addr_type is AddressType.IPV6:
            addr = await self._reader.read(4)
            return socket.inet_ntop(socket.AF_INET6, addr)

    async def handle_connection_request(self) -> None:
        await self._reader.read(1)  # Version, skip
        cmd, = await self._reader.read(1)
        await self._reader.read(1)  # Reserved, skip
        addr = await self._read_address()
        port = await self._reader.read(2)
        port = int.from_bytes(port, "big")

        if cmd not in CommandType._value2member_map_ or cmd not in _SUPPORTED_COMMANDS:
            self._writer.write(_INVALID_COMMAND)
            await self._writer.drain()
            raise Disconnection

        if addr is None:
            self._writer.write(_INVALID_ADDRESS)
            await self._writer.drain()
            raise Disconnection

        command = CommandType(cmd)

        if command is CommandType.CONNECT:
            return await self._handle_connection(addr, port)

        raise RuntimeError("Unreachable")

    async def _handle_connection(self, address: str, port: int) -> None:
        self._dst_reader, self._dst_writer = await asyncio.open_connection(address, port)

        _, port = self._dst_writer.get_extra_info("sockname")
        self._writer.write(CommandReply(
            status=ReplyStatus.SUCCESS,
            address_type=AddressType.IPV4,
            address=self._server.public_ip,
            port=port,  # TODO: or is it port for newly-opened connection?
        ).write())
        await self._writer.drain()

        for callback in self._server.event_handlers.get(ClientEventType.DEST_CONNECT, []):
            asyncio.create_task(callback(self))

        await ClientDstRelay(
            self,
            self._dst_reader,
            self._dst_writer,
            self._server.event_handlers.get(ClientEventType.DATA, []),
            self._server.event_handlers.get(ClientEventType.DATA_MODIFY, []),
        ).run()

    async def _handle_bind(self, address: str, port: int):
        """
        client_connected_fut: asyncio.Future[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Future()

        async def _client_connected(reader_: asyncio.StreamReader, writer_: asyncio.StreamWriter):
            if client_connected_fut.done():
                writer_.close()
                return await writer_.wait_closed()
            client_connected_fut.set_result((reader_, writer_))

        self._bind_server = await asyncio.start_server(_client_connected, self._server.public_ip, 0)
        await self._bind_server.start_serving()
        socket_ = self._bind_server.sockets[0]

        self._writer.write(
            b"\x05\x00\x00\x01"
            + socket.inet_aton(self._server.public_ip)
            + int.to_bytes(socket_.getsockname()[1], 2, "big")
        )
        await self._writer.drain()

        dst_reader, dst_writer = await client_connected_fut

        peername = dst_writer.get_extra_info("sockname")
        self._writer.write(
            b"\x05\x00\x00\x01"
            + socket.inet_aton(peername[0])
            + int.to_bytes(peername[1], 2, "big")
        )
        await self._writer.drain()

        await ClientDstRelay(self, dst_reader, dst_writer, self._server.event_handlers.get("data", [])).run()

        self._bind_server.close()
        await self._bind_server.wait_closed()
        """

        raise NotImplementedError  # TODO: implement bind command

    async def _handle_udp(self, address: str, port: int):
        raise NotImplementedError  # TODO: implement udp command

    def get_rw(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return self._reader, self._writer

    async def write_client(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

    async def write_dst(self, data: bytes) -> None:
        self._dst_writer.write(data)
        await self._dst_writer.drain()
