import asyncio
from typing import Callable, Awaitable

from socks5server.auth import AuthenticationBase, NoAuthentication
from socks5server.client_socks5 import Socks5Client
from socks5server.exceptions import Disconnection
from socks5server.relay import DataDirection

ClientConnectedType = ClientDisconnectedType = Callable[[Socks5Client], Awaitable]
DataCallbackType = Callable[[Socks5Client, DataDirection, bytes], Awaitable]


class SocksServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 1080, no_auth: bool = False):
        self._host = host
        self._port = port

        self._auth_methods: dict[int, AuthenticationBase] = {}
        if no_auth:
            self._auth_methods[0] = NoAuthentication()

        self._event_handlers: dict[str, set[ClientConnectedType]] = {}

    @property
    def event_handlers(self):
        return self._event_handlers

    def register_authentication(self, method: int, cls: AuthenticationBase):
        self._auth_methods[method] = cls

    async def serve(self):
        server = await asyncio.start_server(self.handle_client, self._host, self._port)
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        version = (await reader.read(1))[0]
        if version != 5:
            writer.write(b"\x05\xFF")
            await writer.drain()
            writer.close()
            return

        client = Socks5Client(reader, writer, self)
        for handler in self._event_handlers.get("client_connected", []):
            asyncio.create_task(handler(client))

        try:
            await client.handle()
        except Disconnection:
            writer.close()

        for handler in self._event_handlers.get("client_disconnected", []):
            asyncio.create_task(handler(client))

    def choose_auth_method(self, methods: bytes) -> tuple[int, AuthenticationBase] | None:
        for method in methods:
            if (auth_method := self._auth_methods.get(method, None)) is not None:
                return method, auth_method

    def register_handler(self, event: str, func: ClientConnectedType | DataCallbackType):
        if event not in self._event_handlers:
            self._event_handlers[event] = set()
        self._event_handlers[event].add(func)

    def on_client_connected(self, func: ClientConnectedType):
        self.register_handler("client_connected", func)
        return func

    def on_client_disconnected(self, func: ClientConnectedType):
        self.register_handler("client_disconnected", func)
        return func

    def on_data(self, func: DataCallbackType):
        self.register_handler("data", func)
        return func
