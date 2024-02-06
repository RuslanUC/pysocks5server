# PySocks5Server

Simple socks5 proxy server written in python.

## Installation
**Requirements:**
  - Python 3.10+

```shell
pip install pysocks5server
```

## Usage
```shell
Usage: python -m socks5server [-h] [--host HOST] [--port PORT] [--no-auth] [--users [USERS ...]]

options:
  -h, --help           show this help message and exit
  --host HOST
  --port PORT
  --no-auth            Allow connections without authentication.
  --users [USERS ...]  List of users. Example: "--users user1:password1 user2:password2"
```

## TODO
  - [ ] TCP/IP port binding
  - [ ] UDP port association
  - [ ] Socks4/socks4a support?

## Code examples

### Run server without authentication
```python
from asyncio import get_event_loop
from socks5server import SocksServer

server = SocksServer("0.0.0.0", 1080, True)

if __name__ == '__main__':
    get_event_loop().run_until_complete(server.serve())
```

### Run server with callbacks
```python
from asyncio import get_event_loop
from socks5server import SocksServer, Socks5Client, DataDirection

server = SocksServer("0.0.0.0", 1080, True)

@server.on_client_connected
async def client_connected(client: Socks5Client):
    print(f"Client connected: {client}")
    
    
@server.on_client_disconnected
async def client_disconnected(client: Socks5Client):
    print(f"Client disconnected: {client}")
    
    
@server.on_data
async def data_received(client: Socks5Client, direction: DataDirection, data: bytes):
    print(f"{direction} | {data}")

    
if __name__ == '__main__':
    get_event_loop().run_until_complete(server.serve())
```

### Run server with password authentication
```python
from asyncio import get_event_loop
from socks5server import SocksServer, PasswordAuthentication

server = SocksServer("0.0.0.0", 1080)
users = {"test_login1": "test_password1", "login": "password"}
server.register_authentication(0x02, PasswordAuthentication(users))  # 0x02 is password authentication type

if __name__ == '__main__':
    get_event_loop().run_until_complete(server.serve())
```

### Run server with custom authentication
[All Authentication methods](https://en.wikipedia.org/wiki/SOCKS#:~:text=methods%20supported%2C%20uint8-,AUTH,-Authentication%20methods%2C%201)

```python
import asyncio
from asyncio import get_event_loop
from socks5server import SocksServer, AuthenticationBase


class ChallengeHandshakeAuthentication(AuthenticationBase):
    async def authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        ... # Implement authentication process
    
        return True


server = SocksServer("0.0.0.0", 1080)

# 0x03 is type of Challenge–Handshake Authentication Protocol
server.register_authentication(0x03, ChallengeHandshakeAuthentication())

if __name__ == '__main__':
    get_event_loop().run_until_complete(server.serve())
```
