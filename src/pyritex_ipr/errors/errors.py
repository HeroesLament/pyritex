from oxitrait.enum import Enum, auto

# ========== Errors ==========

class IPRouteError(metaclass=Enum):
    SEND_FAILED = auto()
    RECEIVE_FAILED = auto()
    PARSE_FAILED = auto()
    SOCKET_CLOSED = auto()
    UNKNOWN_ERROR = auto()