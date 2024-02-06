from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING

from socks5server.exceptions import Disconnection
from socks5server.relay import ClientDstRelay

if TYPE_CHECKING:
    from socks5server.server import SocksServer


class Socks5Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server: SocksServer):
        self._reader = reader
        self._writer = writer
        self._server = server

        self._commands = {0x01: self._handle_connection}

    def __repr__(self) -> str:
        addr, port = self._writer.get_extra_info("peername")
        return f"Socks5Client(address={addr!r}, port={port!r})"

    async def handle(self):
        await self.authenticate()
        await self.handle_connection_request()

    async def authenticate(self):
        auth_methods_len = (await self._reader.read(1))[0]
        method = self._server.choose_auth_method(await self._reader.read(auth_methods_len))

        if method is None:
            self._writer.write(b"\x05\xFF")
            await self._writer.drain()
            raise Disconnection

        method_type, auth_method = method

        self._writer.write(bytes([5, method_type]))
        await self._writer.drain()

        if not await auth_method.authenticate(self._reader, self._writer):
            raise Disconnection

    async def _read_address(self) -> str | None:
        addr_type = (await self._reader.read(1))[0]
        if addr_type == 0x01:  # IPv4
            addr = await self._reader.read(4)
            return socket.inet_ntoa(addr)
        elif addr_type == 0x03:  # Domain
            ln = (await self._reader.read(1))[0]
            return (await self._reader.read(ln)).decode("utf8")
        elif addr_type == 0x04:  # IPv6
            addr = await self._reader.read(4)
            return socket.inet_ntop(socket.AF_INET6, addr)

    async def handle_connection_request(self):
        await self._reader.read(1)  # Version
        cmd = (await self._reader.read(1))[0]
        await self._reader.read(1)  # Reserved
        addr = await self._read_address()
        port = await self._reader.read(2)
        port = int.from_bytes(port, "big")

        if cmd not in self._commands:
            # Version (0x05), status (0x07), rsv (0x00), addr type (0x01), addr (0.0.0.0), port (0)
            self._writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            await self._writer.drain()
            raise Disconnection

        if addr is None:
            # Version (0x05), status (0x08), rsv (0x00), addr type (0x01), addr (0.0.0.0), port (0)
            self._writer.write(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            await self._writer.drain()
            raise Disconnection

        await self._commands[cmd](addr, port)

    async def _handle_connection(self, address: str, port: int):
        dst_reader, dst_writer = await asyncio.open_connection(address, port)

        addr, port = dst_writer.get_extra_info("sockname")
        self._writer.write(b"\x05\x00\x00\x01" + socket.inet_aton(addr) + int.to_bytes(port, 2, "big"))
        await self._writer.drain()

        await ClientDstRelay(self, dst_reader, dst_writer, self._server.event_handlers.get("data", [])).run()

    async def _handle_bind(self, address: str, port: int):
        raise NotImplementedError  # TODO: implement bind command

    async def _handle_udp(self, address: str, port: int):
        raise NotImplementedError  # TODO: implement udp command

    def get_rw(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return self._reader, self._writer
