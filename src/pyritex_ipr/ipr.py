import struct
from typing import List

from oxitrait.struct import Struct
from oxitrait.trait import Trait
from oxitrait.impl import Impl
from oxitrait.enum import Enum, auto

from result import Result, Ok, Err
from toolz.curried import pipe, map, filter

import pyritex
from pyritex import (
    AF_INET,
    AF_UNSPEC,
    NETLINK_ROUTE,
    NetlinkHeader,
    NetlinkMessage,
    NetlinkSocket,
    NLMSG_ALIGN,
    RouteMessage,
    IFLA_IFNAME,
    IFLA_OPERSTATE,
    IF_OPER_DOWN,
    IF_OPER_UP,
    RTM_GETLINK,
    RTM_NEWLINK,
    NLA_F_NESTED,
    NLA_F_NET_BYTEORDER,
    NLMSG_HDR_SIZE,
    NLM_F_DUMP, 
    NLM_F_REQUEST,
    RtMsg,
    set_pyritex_log_level,
)

from .errors import IPRouteError


# ========== Enums ==========

class LinkType(metaclass=Enum):
    """Types of links we might encounter."""
    ETHERNET = auto()
    LOOPBACK = auto()
    OTHER = auto()


class LinkState(metaclass=Enum):
    """Administrative state of a link."""
    UP = auto()
    DOWN = auto()
    UNKNOWN = auto()

# ========== Structs ==========

class Link(metaclass=Struct):
    """A parsed network link."""
    index: int
    name: str
    link_type: LinkType
    state: LinkState


# ========== Traits ==========

class IPRouteClientTrait(metaclass=Trait):
    async def link_get(self) -> Result[List[Link], str]:
        """
        Retrieve a list of network interfaces.
        Returns Ok(list_of_links) on success, or Err(error_message) on failure.
        """

class LinkTrait(metaclass=Trait):
    def index(self):
        pass


# ========== Implementation ==========
class ImplLink(LinkTrait, metaclass=Impl, target="Link"):
    def index(self):
        return self.index

class ImplIPRouteClient(IPRouteClientTrait, metaclass=Impl, target="IPRouteClient"):
    async def link_get(self) -> Result[List[Link], IPRouteError]:
        try:
            msg = self.build_link_get_request()
            await self.sock.send(msg)
            responses = await self.sock.receive_message()
            links = self.parse_link_get_responses(responses)
            return Ok(links)
        except Exception:
            return Err(IPRouteError.UNKNOWN_ERROR)


    def build_link_get_request(self) -> Result[NetlinkMessage, str]:
        """
        Build a NetlinkMessage for RTM_GETLINK (dump all interfaces).
        Returns a Result containing the NetlinkMessage.
        """

        # Build payload (RtMsg) first
        payload = RtMsg(
            family=AF_UNSPEC,
            dst_len=None,
            src_len=None,
            tos=None,
            table=None,
            protocol=None,
            scope=None,
            rtm_type=None,
            flags=None,
        )

        payload_bytes_result = payload.to_bytes()
        if payload_bytes_result.is_err():
            return Err(f"Failed to serialize RtMsg: {payload_bytes_result.unwrap_err()}")

        payload_bytes = payload_bytes_result.unwrap()

        # Now build header
        header = NetlinkHeader(
            nlmsg_len=NLMSG_HDR_SIZE + len(payload_bytes),
            nlmsg_type=RTM_GETLINK,
            nlmsg_flags=NLM_F_REQUEST | NLM_F_DUMP,
            nlmsg_seq=0,
            nlmsg_pid=0,
        )

        # Finally compose into NetlinkMessage
        message = NetlinkMessage(
            header=header,
            payload=payload
        )

        return Ok(message)


    def parse_attributes(self, payload: bytes) -> Result[dict[int, bytes], str]:
        """
        Parse Netlink attributes from a payload into a {type: value} dictionary.
        Returns Ok(attrs) on success or Err(str) on failure.
        """

        attrs = {}
        offset = 0
        total_len = len(payload)

        while offset + 4 <= total_len:
            try:
                nla_len, nla_type = struct.unpack_from("HH", payload, offset)
            except struct.error as e:
                return Err(f"Failed to unpack attribute header at offset {offset}: {e}")

            if nla_len < 4 or offset + nla_len > total_len:
                return Err(f"Malformed attribute at offset {offset}: nla_len={nla_len}, total_len={total_len}")

            real_type = nla_type & ~(NLA_F_NESTED | NLA_F_NET_BYTEORDER)

            value = payload[offset + 4 : offset + nla_len]
            attrs[real_type] = value

            offset += (nla_len + 3) & ~3  # 4-byte aligned

        return Ok(attrs)


    def parse_link_get_responses(self, responses: List[NetlinkMessage]) -> List[Link]:
        """
        Parse a list of NetlinkMessages (RTM_NEWLINK responses) into Link structs.
        """
        def decode_link(message: NetlinkMessage) -> Link | None:
            if message.header.nlmsg_type() != RTM_NEWLINK:
                return None

            if isinstance(message.payload, RtMsg):
                rtm = message.payload
            else:
                return None

            payload_bytes_result = rtm.to_bytes()
            if payload_bytes_result.is_err():
                return None

            payload_bytes: bytes = payload_bytes_result.unwrap()

            attrs_result = self.parse_attributes(payload_bytes[4:])
            if attrs_result.is_err():
                return None
            attrs = attrs_result.unwrap()

            link_name = attrs.get(IFLA_IFNAME)
            operstate = attrs.get(IFLA_OPERSTATE)

            if link_name is None:
                return None

            name = link_name.decode('utf-8').rstrip('\x00')

            state = {
                IF_OPER_UP: LinkState.UP,
                IF_OPER_DOWN: LinkState.DOWN,
            }.get(
                int.from_bytes(operstate, byteorder='little') if operstate else None,
                LinkState.UNKNOWN
            )

            return Link(
                index=rtm.index,
                name=name,
                link_type=LinkType.ETHERNET,
                state=state,
            )

        return pipe(
            responses,
            map(decode_link),
            filter(lambda link: link is not None),
            list,
        )


# ========== Public Struct ==========

class IPRouteClient(metaclass=Struct):
    sock: NetlinkSocket
