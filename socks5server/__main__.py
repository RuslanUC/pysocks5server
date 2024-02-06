from argparse import ArgumentParser, Namespace
from asyncio import get_event_loop

from socks5server import SocksServer, PasswordAuthentication, Socks5Client

parser = ArgumentParser()
parser.add_argument("--host", type=str, default="0.0.0.0", required=False)
parser.add_argument("--port", type=int, default=1080, required=False)
parser.add_argument("--no-auth", action="store_true", default=False, required=False,
                    help="Allow connections without authentication.")
parser.add_argument("--users", nargs="*", default=[], required=False,
                    help="List of users. Example: \"--users user1:password1 user2:password2\"")


class Args(Namespace):
    host: str
    port: int
    no_auth: bool
    users: list[str]


args = parser.parse_args(namespace=Args())
server = SocksServer(args.host, args.port, args.no_auth)

if args.users:
    users = {login: password for user in args.users for login, password in [user.split(":")]}
    auth = PasswordAuthentication(users)
    server.register_authentication(0x02, auth)
    print("Registered users: " + ", ".join(users.keys()))


@server.on_client_connected
async def on_client_connected(client: Socks5Client):
    print(f"Client connected: {client}!")


@server.on_client_disconnected
async def on_client_disconnected(client: Socks5Client):
    print(f"Client disconnected: {client}!")


if __name__ == '__main__':
    print("Server running")
    get_event_loop().run_until_complete(server.serve())
