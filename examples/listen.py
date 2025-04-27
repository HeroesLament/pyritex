# Standard Library
import struct
import logging

# Third-party
import anyio
from anyio import create_task_group

# Internal
import pyritex
from pyritex import (
    NetlinkSocket,
    IFLA_IFNAME,
    NETLINK_ROUTE,
    NLMSG_ALIGN,
    RTNLGRP_LINK,
    RTM_DELLINK,
    RTM_NEWLINK,
    set_pyritex_log_level
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

set_pyritex_log_level(5)

def parse_ifname(attrs: list[tuple[int, bytes]]) -> str:
    for atype, data in attrs:
        if atype == IFLA_IFNAME:
            return data.rstrip(b"\x00").decode()
    return "<unknown>"

def parse_link_attrs(payload: bytes):
    if len(payload) < 16:
        return {"error": "Invalid ifinfomsg: too short"}

    try:
        _, _, _, _, _, _ = struct.unpack("=BBHiII", payload[:16])
    except Exception as e:
        return {"error": f"Failed to unpack ifinfomsg: {e}"}

    attrs = []
    offset = 16
    while offset + 4 <= len(payload):
        try:
            rlen, rtype = struct.unpack_from("=HH", payload, offset)
            if rlen < 4 or offset + rlen > len(payload):
                break
            rdata = payload[offset+4 : offset+rlen]
            attrs.append((rtype, rdata))
            offset = NLMSG_ALIGN(offset + rlen)
        except Exception:
            break

    return {
        "attrs": attrs,
    }

async def main():
    async with create_task_group() as tg:
        async with NetlinkSocket(protocol=NETLINK_ROUTE, groups=[RTNLGRP_LINK]) as pyr:
            async for hdr, payload in pyr.listen():
                msg_type = hdr["type"]

                if msg_type not in (RTM_NEWLINK, RTM_DELLINK):
                    continue  # not an up/down event

                parsed = parse_link_attrs(payload)
                if "error" in parsed:
                    print("Parse error:", parsed["error"])
                    continue

                ifname = parse_ifname(parsed["attrs"])
                if msg_type == RTM_NEWLINK:
                    print(f" Interface UP: {ifname}")
                elif msg_type == RTM_DELLINK:
                    print(f" Interface DOWN: {ifname}")

anyio.run(main)
