from abc import abstractmethod

import logging
import struct
import trio
from typing import List, Dict, Any, Tuple

from oxitrait.enum import Enum, auto
from oxitrait.struct import Struct
from oxitrait.impl import Impl
from oxitrait.trait import Trait
from oxitrait.runtime import requires_traits

from pyritex import NetlinkSocket, RouteMessage, set_log_level
from pyritex.netlink.message import RtMsg, NetlinkHeader
from pyritex.netlink.consts import *
from pyritex.netlink.rtnl.consts import *
from result import Result, Ok, Err

class MyEnum(metaclass=Enum):
    RED = auto()
    BLUE = auto()

class myTrait(metaclass=Trait):
    def thing1(self):
        pass

class MyOtherTrait(metaclass=Trait):
    def thing2(self):
        pass

class Impl1(myTrait, metaclass=Impl, target="MyEnum"):
    def thing1(self):
        pass

class Impl2(MyOtherTrait, metaclass=Impl, target="MyEnum"):
    def thing2(self):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

set_log_level(30)  # Enable detailed logging

def parse_netlink_message(data: bytes) -> Result:
    """Parse complete netlink messages including headers and nested messages."""
    results = []
    offset = 0
    
    try:
        while offset + 16 <= len(data):
            # Parse Netlink header (16 bytes)
            try:
                msg_len, msg_type, flags, seq, pid = struct.unpack("=LHHLL", data[offset:offset+16])
            except struct.error:
                return Err(f"Failed to unpack Netlink header at offset {offset}")
                
            if msg_len < 16:
                return Err(f"Invalid message length {msg_len}")
                
            # Extract payload for this message
            if offset + msg_len > len(data):
                return Err(f"Message length {msg_len} extends beyond buffer size")
                
            payload = data[offset+16:offset+msg_len]
            
            # If this is a route message, parse it
            if msg_type == RTM_NEWROUTE:
                if len(payload) >= 12:
                    route_info = parse_rtnl_message(payload)
                    results.append(route_info)
                else:
                    return Err(f"Payload too short for RTM_NEWROUTE message")
            
            # Move to next message
            offset += msg_len
            offset = (offset + 3) & ~3
    except Exception as e:
        return Err(f"Error during Netlink message parsing: {str(e)}")
    
    return Ok(results)

def parse_rtattr(payload):
    """Parses Netlink route attributes (NLA) from raw payload bytes."""
    attrs = []
    offset = 0

    while offset + 4 <= len(payload):
        try:
            attr_len, attr_type = struct.unpack("HH", payload[offset:offset+4])
            
            if attr_len < 4:
                print(f"Warning: Invalid attribute length {attr_len} at offset {offset}")
                break
                
            # Make sure we don't read past the end of the payload
            if offset + attr_len > len(payload):
                print(f"Warning: Attribute extends beyond payload boundary")
                break
                
            attr_data = payload[offset+4:offset+attr_len]
            
            # Convert known types to readable formats
            if attr_type in (RTA_DST, RTA_GATEWAY, RTA_PREFSRC):
                if len(attr_data) == 4:  # IPv4 address
                    attr_value = ".".join(map(str, attr_data))  # Convert binary IP to string
                else:
                    attr_value = attr_data  # Raw value for non-IPv4
            elif attr_type == RTA_OIF:
                if len(attr_data) == 4:
                    attr_value = int.from_bytes(attr_data, "little")  # Interface index
                else:
                    attr_value = attr_data
            else:
                attr_value = attr_data  # Raw value for unknown types
            
            attrs.append((attr_type, attr_value))
            
            # Move to next attribute with alignment
            offset += (attr_len + 3) & ~3
        except struct.error:
            print(f"Error unpacking attribute at offset {offset}")
            break
        except Exception as e:
            print(f"Error parsing attribute: {e}")
            break
    
    return attrs

def parse_rtnl_message(payload):
    """Decodes RTNL Route Message (RTM_GETROUTE response)."""
    if len(payload) < 12:
        return {"error": "Invalid RTM message: Too short"}

    try:
        # Extract the rtmsg structure (first 12 bytes)
        family, dst_len, src_len, tos, table, protocol, scope, route_type, flags = struct.unpack("BBBBBBBBI", payload[:12])
    except struct.error:
        return {"error": "Failed to unpack rtmsg structure"}

    # Extract Netlink attributes (rest of payload)
    attrs = parse_rtattr(payload[12:])

    return {
        "family": family,
        "dst_len": dst_len,
        "src_len": src_len,
        "table": table,
        "protocol": protocol,
        "scope": scope,
        "type": route_type,
        "flags": flags,
        "attrs": attrs,
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

    async with trio.open_nursery() as pyr_nursery:
        async with NetlinkSocket(protocol=NETLINK_ROUTE, nursery=pyr_nursery) as pyr:
            send_res = await pyr.send_message(msg_bytes)
            if send_res.is_err():
                print("Send error:", send_res.unwrap_err())
                return

            recv_res = await pyr.receive_message(timeout=1.0)

    if recv_res is None:
        print("No message received!")
        return
    if recv_res.is_err():
        print("Receive error:", recv_res.unwrap_err())
        return

    inbound_msg = recv_res.unwrap()
    
    # Parse all route messages from the response
    parse_result = parse_netlink_message(inbound_msg["payload"])
    if parse_result.is_err():
        print("Parse error:", parse_result.unwrap_err())
        # Fallback to the original single-message parsing method
        route_info = parse_rtnl_message(inbound_msg["payload"])
        print("\n=== Parsed Single RTM_GETROUTE Response (Fallback) ===")
        for key, value in route_info.items():
            if key == "attrs":
                print("Attributes:")
                for attr in value:
                    print(f"  {attr[0]}: {attr[1]}")
            else:
                print(f"{key}: {value}")
        return
        
    all_routes = parse_result.unwrap()
    
    print(f"\n=== Parsed {len(all_routes)} Route Messages ===")
    for i, route in enumerate(all_routes):
        print(f"\nRoute #{i+1}:")
        for key, value in route.items():
            if key == "attrs":
                print("  Attributes:")
                for attr in value:
                    print(f"    {attr[0]}: {attr[1]}")
            else:
                print(f"  {key}: {value}")

trio.run(main)