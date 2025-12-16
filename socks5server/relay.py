from __future__ import annotations

import asyncio
from enum import auto, Enum
from typing import Iterable, TYPE_CHECKING

from socks5server.enums import DataModify
from socks5server.exceptions import Disconnection

if TYPE_CHECKING:
    from socks5server.client_socks5 import Socks5Client
    from socks5server.server import DataCallbackType, ModifyCallbackType


class DataDirection(Enum):
    CLIENT_TO_DST = auto()
    DST_TO_CLIENT = auto()


class ClientDstRelay:
    def __init__(
            self, client: Socks5Client, dst_reader: asyncio.StreamReader, dst_writer: asyncio.StreamWriter,
            data_callbacks: Iterable[DataCallbackType], modify_callbacks: Iterable[ModifyCallbackType],
    ) -> None:
        self.client = client
        self._cl_reader, self._cl_writer = client.get_rw()
        self._dst_reader = dst_reader
        self._dst_writer = dst_writer
        self._data_callbacks = data_callbacks
        self._modify_callbacks = modify_callbacks

    def _callback(self, direction: DataDirection, data: bytes) -> None:
        for callback in self._data_callbacks:
            asyncio.create_task(callback(self.client, direction, data))

    async def _exec_modify_callbacks(self, direction: DataDirection, data: bytes) -> bytes | None:
        for callback in self._modify_callbacks:
            result = await callback(self.client, direction, data)
            if isinstance(result, bytes):
                return result
            if result is DataModify.DONT_SEND:
                return None

        return data

    async def _client_to_dst(self) -> None:
        while data := await self._cl_reader.read(1024 * 32):
            self._callback(DataDirection.CLIENT_TO_DST, data)
            data = await self._exec_modify_callbacks(DataDirection.CLIENT_TO_DST, data)
            if data is None:
                continue
            self._dst_writer.write(data)
            await self._dst_writer.drain()

        self._dst_writer.close()

    async def _dst_to_client(self) -> None:
        while data := await self._dst_reader.read(1024 * 32):
            self._callback(DataDirection.DST_TO_CLIENT, data)
            data = await self._exec_modify_callbacks(DataDirection.CLIENT_TO_DST, data)
            if data is None:
                continue
            self._cl_writer.write(data)
            await self._cl_writer.drain()

        self._cl_writer.close()

    async def run(self) -> None:
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
