from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"


class DeviceTrust(StrEnum):
    LIMITED = "limited"
    TRUSTED = "trusted"


class AuthenticationStrength(StrEnum):
    PASSKEY = "passkey"
    PASSKEY_TOTP = "passkey_totp"
    DEVELOPMENT = "development"


class ChallengeKind(StrEnum):
    PASSKEY_REGISTRATION = "passkey_registration"
    PASSKEY_AUTHENTICATION = "passkey_authentication"


class SecurityApprovalDecision(StrEnum):
    ALLOW_ONCE = "allow_once"
    ALLOW_FOR_TASK = "allow_for_task"
    REJECT = "reject"
    MODIFY = "modify"


class GrantStatus(StrEnum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class LockdownState(StrEnum):
    NORMAL = "normal"
    LOCKED_DOWN = "locked_down"
