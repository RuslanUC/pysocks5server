import asyncio
from abc import ABC, abstractmethod


class AuthenticationBase(ABC):
    @abstractmethod
    async def authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool: ...


class NoAuthentication(AuthenticationBase):
    async def authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        return True


class PasswordAuthentication(AuthenticationBase):
    def __init__(self, users: dict[str, str]):
        self._users = users

    async def authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        await reader.read(1)
        login_len = (await reader.read(1))[0]
        login = (await reader.read(login_len)).decode("utf8")
        passw_len = (await reader.read(1))[0]
        passw = (await reader.read(passw_len)).decode("utf8")

        if login not in self._users or self._users[login] != passw:
            writer.write(b"\x01\xFF")
            await writer.drain()
            return False

        writer.write(b"\x01\x00")
        await writer.drain()
        return True
