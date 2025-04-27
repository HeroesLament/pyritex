import anyio
import struct
import logging
from abc import abstractmethod
from typing import Any, Tuple, Optional

from anyio import create_memory_object_stream
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from result import Result, Ok, Err

from pyritex import NetlinkSocket, RouteMessage
from pyritex.netlink.message import RtMsg, NetlinkHeader
from pyritex.netlink.consts import *
from pyritex.netlink.rtnl.consts import *

from oxitrait.struct import Struct
from oxitrait.trait import Trait
from oxitrait.impl import Impl
from oxitrait.runtime import requires_traits

# --- Message types ---

class RouteRequest:
    def __init__(self, reply_chan: MemoryObjectSendStream):
        self.reply_chan = reply_chan

class ChannelPackTrait(metaclass=Trait):
    @abstractmethod
    def rx(self):
        ...

class ActorTrait(metaclass=Trait):
    @abstractmethod
    @requires_traits(channels=ChannelPackTrait)
    async def run(self, channels: Any):
        """Main entrypoint. Receives a ChannelPack."""
        pass

class ImplChanPackSocket(ChannelPackTrait, metaclass=Impl, target="SocketChannelPack"):
    def rx(self):
        return self.rx

class ImplChanPackRoute(ChannelPackTrait, metaclass=Impl, target="RouteChannelPack"):
    def rx(self):
        return self.rx

class SocketChannelPack(metaclass=Struct):
    """
    :params:
    rx: MemoryObjectSendStream
    """
    rx: MemoryObjectReceiveStream

class RouteChannelPack(metaclass=Struct):
    """
    :params:
      rx: MemoryObjectReceiveStream

     sock_tx: MemoryObjectSendStream
    """
    rx: Optional[MemoryObjectReceiveStream] = None
    sock_tx: Optional[MemoryObjectSendStream] = None

class ImplSocketActor(ActorTrait, metaclass=Impl, target="SocketActor"):
    async def run(self, channels: SocketChannelPack):
        async with NetlinkSocket(protocol=NETLINK_ROUTE) as sock:
            async for msg in channels.rx:
                if isinstance(msg, RouteRequest):
                    hdr = NetlinkHeader()
                    rtm = RtMsg(family=int(AF_INET), table=RT_TABLE_MAIN)
                    req = RouteMessage(hdr, rtm, b"")
                    bytes_result = req.to_bytes()
                    if bytes_result.is_err():
                        await msg.reply_chan.send({"error": "serialization"})
                        continue

                    send_res = await sock.send_message(bytes_result.unwrap())
                    if send_res.is_err():
                        await msg.reply_chan.send({"error": "send"})
                        continue

                    recv_res = await sock.receive_message(timeout=5.0)
                    if recv_res is None or recv_res.is_err():
                        await msg.reply_chan.send({"error": "recv"})
                        continue

                    await msg.reply_chan.send(recv_res.unwrap())

class ImplRouteActor(ActorTrait, metaclass=Impl, target="RouteActor"):
    async def run(self, channels: RouteChannelPack):
        reply_send, reply_recv = create_memory_object_stream(1)
        await channels.sock_tx.send(RouteRequest(reply_send))

        response = await reply_recv.receive()
        if "error" in response:
            print("Route actor: error:", response["error"])
            return

        parsed = parse_rtnl_message(response["payload"])
        print("Parsed route:")
        for k, v in parsed.items():
            print(f"  {k}: {v}")

class SocketActor(metaclass=Struct):
    pass

class RouteActor(metaclass=Struct):
    pass



# --- Route consumer actor ---

def parse_rtattr(payload: bytes):
    def extract_attr(offset):
        if offset + 4 > len(payload): return None
        alen, atype = struct.unpack_from("=HH", payload, offset)
        if alen < 4 or offset + alen > len(payload): return None
        data = payload[offset + 4 : offset + alen]
        if atype in (RTA_DST, RTA_GATEWAY, RTA_PREFSRC) and len(data) == 4:
            value = ".".join(map(str, data))
        elif atype == RTA_OIF and len(data) == 4:
            value = int.from_bytes(data, "little")
        else:
            value = data
        return (offset + NLMSG_ALIGN(alen), (atype, value))

    attrs, offset = [], 0
    while True:
        res = extract_attr(offset)
        if not res: break
        offset, attr = res
        attrs.append(attr)
    return attrs

def parse_rtnl_message(payload):
    if len(payload) < 12:
        return {"error": "short"}
    try:
        fields = struct.unpack("=BBBBBBBBI", payload[:12])
        family, dst_len, src_len, tos, table, proto, scope, route_type, flags = fields
        attrs = dict(parse_rtattr(payload[12:]))
        return {
            "family": family,
            "table": table,
            "protocol": proto,
            "scope": scope,
            "type": route_type,
            "flags": flags,
            "attrs": attrs,
        }
    except Exception as e:
        return {"error": str(e)}

# --- Entrypoint ---

async def main():
    sock_tx, sock_rx = anyio.create_memory_object_stream(10)
    route_tx, route_rx = anyio.create_memory_object_stream(10)

    sock = SocketActor()
    route = RouteActor()
    sock_cp = SocketChannelPack(sock_rx)
    route_cp = RouteChannelPack(
        route_rx,
        sock_tx
    )

    async with anyio.create_task_group() as tg:
        tg.start_soon(sock.run, sock_cp)
        tg.start_soon(route.run, route_cp)

anyio.run(main)
