import trio
from typing import Optional

running = True

send_chan, recv_chan = trio.open_memory_channel(max_buffer_size=100)

class Container():
    socket: Optional[trio.socket.SocketType] = None

    def __init__(self, socket: trio.socket.SocketType = None):
        self.socket = socket

    async def start(self):
        async with trio.open_nursery() as nursury:
            nursury.start_soon(self.read_loop)

    async def read_loop(self):
        while running is True:
            self.socket.recv(65536)

async def setup_socket() -> trio.socket.SocketType:
    sock = trio.socket.socket(16, trio.socket.SOCK_RAW, 0)
    await sock.bind((0,0))
    return sock


async def main():
    sock = await setup_socket()
    cont = Container(socket=sock)
    await cont.start()


trio.run(main)