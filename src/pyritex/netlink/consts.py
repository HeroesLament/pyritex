import socket
import struct

# Address family constants
AF_INET = getattr(socket, 'AF_INET', 2)
AF_NETLINK = getattr(socket, 'AF_NETLINK', 16)  # Default to 16 for Linux compatibility
AF_BRIDGE = getattr(socket, 'AF_BRIDGE', 7)    # Default to 7 for bridge sockets

# Interface constants
IFLA_IFNAME = 3

# Interface Flags (from if.h)
IFF_LOWER_UP = 0x10000
IFF_DORMANT = 0x20000

# Link Attribute Types (IFLA_*)
IFLA_WIRELESS = 11
IFLA_OPERSTATE = 16
IFLA_LINKMODE = 17

# Interface Operational States
IF_OPER_DORMANT = 5
IF_OPER_UP = 6

# Multicast Group Index
RTNLGRP_LINK = 1

# Protocol-specific constants
SOL_NETLINK = getattr(socket, 'SOL_NETLINK', 270)  # Default to 270 for Netlink-specific socket options

# General constants
NLMSG_MIN_TYPE = 0x10

GENL_NAMSIZ = 16  # Length of family name
GENL_MIN_ID = NLMSG_MIN_TYPE
GENL_MAX_ID = 1023

GENL_ADMIN_PERM = 0x01
GENL_CMD_CAP_DO = 0x02
GENL_CMD_CAP_DUMP = 0x04
GENL_CMD_CAP_HASPOL = 0x08

# Reserved static generic netlink identifiers
GENL_ID_GENERATE = 0
GENL_ID_CTRL = NLMSG_MIN_TYPE

# Controller commands
CTRL_CMD_UNSPEC = 0x0
CTRL_CMD_NEWFAMILY = 0x1
CTRL_CMD_DELFAMILY = 0x2
CTRL_CMD_GETFAMILY = 0x3
CTRL_CMD_NEWOPS = 0x4
CTRL_CMD_DELOPS = 0x5
CTRL_CMD_GETOPS = 0x6
CTRL_CMD_NEWMCAST_GRP = 0x7
CTRL_CMD_DELMCAST_GRP = 0x8
CTRL_CMD_GETMCAST_GRP = 0x9
CTRL_CMD_GETPOLICY = 0xA

# Controller attributes
CTRL_ATTR_UNSPEC = 0x0
CTRL_ATTR_FAMILY_ID = 0x1
CTRL_ATTR_FAMILY_NAME = 0x2
CTRL_ATTR_VERSION = 0x3
CTRL_ATTR_HDRSIZE = 0x4
CTRL_ATTR_MAXATTR = 0x5
CTRL_ATTR_OPS = 0x6
CTRL_ATTR_MCAST_GROUPS = 0x7
CTRL_ATTR_POLICY = 0x8
CTRL_ATTR_OP_POLICY = 0x9
CTRL_ATTR_OP = 0xA

CTRL_ATTR_OP_UNSPEC = 0x0
CTRL_ATTR_OP_ID = 0x1
CTRL_ATTR_OP_FLAGS = 0x2

CTRL_ATTR_MCAST_GRP_UNSPEC = 0x0
CTRL_ATTR_MCAST_GRP_NAME = 0x1
CTRL_ATTR_MCAST_GRP_ID = 0x2

# Netlink attribute types
NL_ATTR_TYPE_INVALID = 0
NL_ATTR_TYPE_FLAG = 1
NL_ATTR_TYPE_U8 = 2
NL_ATTR_TYPE_U16 = 3
NL_ATTR_TYPE_U32 = 4
NL_ATTR_TYPE_U64 = 5
NL_ATTR_TYPE_S8 = 6
NL_ATTR_TYPE_S16 = 7
NL_ATTR_TYPE_S32 = 8
NL_ATTR_TYPE_S64 = 9
NL_ATTR_TYPE_BINARY = 10
NL_ATTR_TYPE_STRING = 11
NL_ATTR_TYPE_NUL_STRING = 12
NL_ATTR_TYPE_NESTED = 13
NL_ATTR_TYPE_NESTED_ARRAY = 14
NL_ATTR_TYPE_BITFIELD32 = 15

# Netlink policy attributes
NL_POLICY_TYPE_ATTR_UNSPEC = 0
NL_POLICY_TYPE_ATTR_TYPE = 1
NL_POLICY_TYPE_ATTR_MIN_VALUE_S = 2
NL_POLICY_TYPE_ATTR_MAX_VALUE_S = 3
NL_POLICY_TYPE_ATTR_MIN_VALUE_U = 4
NL_POLICY_TYPE_ATTR_MAX_VALUE_U = 5
NL_POLICY_TYPE_ATTR_MIN_LENGTH = 6
NL_POLICY_TYPE_ATTR_MAX_LENGTH = 7
NL_POLICY_TYPE_ATTR_POLICY_IDX = 8
NL_POLICY_TYPE_ATTR_POLICY_MAXTYPE = 9
NL_POLICY_TYPE_ATTR_BITFIELD32_MASK = 10
NL_POLICY_TYPE_ATTR_PAD = 11
NL_POLICY_TYPE_ATTR_MASK = 12

# Netlink families
NETLINK_ROUTE = 0
NETLINK_UNUSED = 1
NETLINK_USERSOCK = 2
NETLINK_FIREWALL = 3
NETLINK_SOCK_DIAG = 4
NETLINK_NFLOG = 5
NETLINK_XFRM = 6
NETLINK_SELINUX = 7
NETLINK_ISCSI = 8
NETLINK_AUDIT = 9
NETLINK_FIB_LOOKUP = 10
NETLINK_CONNECTOR = 11
NETLINK_NETFILTER = 12
NETLINK_IP6_FW = 13
NETLINK_DNRTMSG = 14
NETLINK_KOBJECT_UEVENT = 15
NETLINK_GENERIC = 16
NETLINK_SCSITRANSPORT = 18

# Netlink attribute flags
NLA_F_NESTED = 1 << 15
NLA_F_NET_BYTEORDER = 1 << 14

# Netlink message flags (nlmsghdr.flags)
NLM_F_REQUEST = 1
NLM_F_MULTI = 2
NLM_F_ACK = 4
NLM_F_ECHO = 8
NLM_F_DUMP_INTR = 0x10
NLM_F_DUMP_FILTERED = 0x20

# Modifiers to GET request
NLM_F_ROOT = 0x100
NLM_F_MATCH = 0x200
NLM_F_ATOMIC = 0x400
NLM_F_DUMP = NLM_F_ROOT | NLM_F_MATCH

# Modifiers to NEW request
NLM_F_REPLACE = 0x100
NLM_F_EXCL = 0x200
NLM_F_CREATE = 0x400
NLM_F_APPEND = 0x800

NLM_F_CAPPED = 0x100
NLM_F_ACK_TLVS = 0x200

# Netlink message types
NLMSG_NOOP = 0x1
NLMSG_ERROR = 0x2
NLMSG_DONE = 0x3
NLMSG_OVERRUN = 0x4
NLMSG_CONTROL = 0xE
NLMSG_TRANSPORT = 0xF
NLMSG_MIN_TYPE = 0x10
NLMSG_MAX_LEN = 0xFFFF

# Netlink header misc
NLMSG_HDR_FORMAT = "IHHII"   # length (I), type (H), flags (H), sequence (I)
NLMSG_HDR_SIZE   = struct.calcsize(NLMSG_HDR_FORMAT)

# Miscellaneous
SOL_NETLINK = 270
NETLINK_ADD_MEMBERSHIP = 1
NETLINK_DROP_MEMBERSHIP = 2
NETLINK_PKTINFO = 3
NETLINK_BROADCAST_ERROR = 4
NETLINK_NO_ENOBUFS = 5
NETLINK_RX_RING = 6
NETLINK_TX_RING = 7
NETLINK_LISTEN_ALL_NSID = 8
NETLINK_EXT_ACK = 11
NETLINK_GET_STRICT_CHK = 12

#  Alignment
NLMSG_ALIGNTO = 4
def NLMSG_ALIGN(length: int) -> int:
    return (length + NLMSG_ALIGNTO - 1) & ~(NLMSG_ALIGNTO - 1)

def NLMSG_LENGTH(payload_len: int) -> int:
    return payload_len + NLMSG_ALIGN(NLMSG_HDR_SIZE)

def NLMSG_SPACE(payload_len: int) -> int:
    return NLMSG_ALIGN(NLMSG_LENGTH(payload_len))