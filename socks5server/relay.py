from __future__ import annotations

import asyncio
from enum import auto, Enum
from typing import Iterable, TYPE_CHECKING

from socks5server.exceptions import Disconnection

if TYPE_CHECKING:
    from socks5server.client_socks5 import Socks5Client
    from socks5server.server import DataCallbackType


class DataDirection(Enum):
    CLIENT_TO_DST = auto()
    DST_TO_CLIENT = auto()


class ClientDstRelay:
    def __init__(self, client: Socks5Client, dst_reader: asyncio.StreamReader, dst_writer: asyncio.StreamWriter,
                 data_callbacks: Iterable[DataCallbackType]):
        self.client = client
        self._cl_reader, self._cl_writer = client.get_rw()
        self._dst_reader = dst_reader
        self._dst_writer = dst_writer
        self._callbacks = data_callbacks

    def _callback(self, direction: DataDirection, data: bytes):
        for callback in self._callbacks:
            asyncio.create_task(callback(self.client, direction, data))

    async def _client_to_dst(self):
        while data := await self._cl_reader.read(1024 * 32):
            self._dst_writer.write(data)
            await self._dst_writer.drain()
            self._callback(DataDirection.CLIENT_TO_DST, data)

        self._dst_writer.close()

    async def _dst_to_client(self):
        while data := await self._dst_reader.read(1024 * 32):
            self._cl_writer.write(data)
            await self._cl_writer.drain()
            self._callback(DataDirection.DST_TO_CLIENT, data)

        self._cl_writer.close()

    async def run(self):
        try:
            await asyncio.gather(
                asyncio.create_task(self._client_to_dst()),
                asyncio.create_task(self._dst_to_client())
            )
        except ConnectionResetError:
            pass

        self._dst_writer.close()
        await self._dst_writer.wait_closed()

        raise Disconnection
