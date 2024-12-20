from enum import Enum

class AppStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CONNECTING = "connecting"
    NOT_CONNECTED = "not_connected"
    PERMISSION_REVOKED = "permission_revoked"