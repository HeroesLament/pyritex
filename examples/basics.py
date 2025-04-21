import anyio
import logging
import struct

from anyio import create_task_group
from result import Result, Ok, Err
from toolz.curried import pipe, map, filter, groupby

from oxitrait.enum import Enum, auto
from oxitrait.struct import Struct
from oxitrait.impl import Impl
from oxitrait.trait import Trait
from oxitrait.runtime import requires_traits

from pyritex import NetlinkSocket, RouteMessage, set_log_level
from pyritex.netlink.message import RtMsg, NetlinkHeader
from pyritex.netlink.consts import *
from pyritex.netlink.rtnl.consts import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

set_log_level(30)

def nlattr_stream(payload: bytes):
    """Yield (type, data) pairs from netlink attribute section."""
    off = 0
    while off + 4 <= len(payload):
        alen, atype = struct.unpack_from("=HH", payload, off)
        if alen < 4 or off + alen > len(payload):
            break  # malformed or truncated attr
        data = payload[off+4 : off+alen]
        yield (atype, data)
        off = NLMSG_ALIGN(off + alen)

def parse_rtattr(payload):
    def extract_attr(offset):
        if offset + 4 > len(payload):
            return None

        alen, atype = struct.unpack_from("=HH", payload, offset)
        if alen < 4 or offset + alen > len(payload):
            return None

        data = payload[offset + 4 : offset + alen]

        if atype in (RTA_DST, RTA_GATEWAY, RTA_PREFSRC) and len(data) == 4:
            value = ".".join(map(str, data))
        elif atype == RTA_OIF and len(data) == 4:
            value = int.from_bytes(data, "little")
        else:
            value = data

        return (offset + NLMSG_ALIGN(alen), (atype, value))

    attrs = []
    offset = 0
    while True:
        result = extract_attr(offset)
        if not result:
            break
        offset, attr = result
        attrs.append(attr)

    return attrs

def parse_rtnl_message(payload):
    print(f"parse_rtnl_message(): payload len={len(payload)}")

    if len(payload) < 12:
        return {"error": "Invalid RTM message: Too short"}

    try:
        rt_fields = struct.unpack("=BBBBBBBBI", payload[:12])
        print(f"rtmsg fields: {rt_fields}")
        family, dst_len, src_len, tos, table, protocol, scope, route_type, flags = rt_fields
    except struct.error as e:
        return {"error": f"Failed to unpack rtmsg: {e}"}

    attrs = parse_rtattr(payload[12:])
    print(f"🧩 Parsed {len(attrs)} route attribute(s)")
    return {
        "family": family,
        "dst_len": dst_len,
        "src_len": src_len,
        "table": table,
        "protocol": protocol,
        "scope": scope,
        "type": route_type,
        "flags": flags,
        "attrs": dict(attrs),
    }

async def main():
    hdr = NetlinkHeader()
    rtm = RtMsg(family=int(AF_INET), table=RT_TABLE_MAIN)
    msg = RouteMessage(hdr, rtm, b"")

    msg_bytes_result = msg.to_bytes()
    if msg_bytes_result.is_err():
        print("Serialization error:", msg_bytes_result.unwrap_err())
        return
    msg_bytes = msg_bytes_result.unwrap()

    async with create_task_group() as tg:
        async with NetlinkSocket(protocol=NETLINK_ROUTE) as pyr:
            send_res = await pyr.send_message(msg_bytes)
            if send_res.is_err():
                print("Send error:", send_res.unwrap_err())
                return

            recv_res = await pyr.receive_message(timeout=5.0)
            if recv_res is None:
                print("No message received!")
                return
            if recv_res.is_err():
                print("Receive error:", recv_res.unwrap_err())
                return

            inbound_msg = recv_res.unwrap()
            print("Raw message received from Netlink:")
            print(inbound_msg)

            if "payload" not in inbound_msg or not inbound_msg["payload"]:
                print("Message has no payload to parse")
                return

            # Correct function to parse a single RtMsg payload
            route = parse_rtnl_message(inbound_msg["payload"])
            if "error" in route:
                print("Failed to parse route:", route["error"])
                return

            print("\n=== Parsed Single Route Message ===")
            for key, value in route.items():
                if key == "attrs":
                    print("  Attributes:")
                    for attr_type, attr_value in value.items():
                        print(f"    {attr_type}: {attr_value}")
                else:
                    print(f"  {key}: {value}")

anyio.run(main)