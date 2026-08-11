from urllib.parse import urlparse

from agentgraph.models.contracts import ModelErrorCode, ModelRouterError


def require_safe_base_url(base_url: str, *, credentialed: bool, loopback_only: bool = False) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Provider base URL is invalid")
    loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if loopback_only and not loopback:
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Provider must use a loopback URL")
    if credentialed and parsed.scheme != "https" and not loopback:
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Credentials require HTTPS")
    return base_url.rstrip("/")


def optional_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "Provider returned invalid usage metadata")
    return value


def optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 500:
        raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "Provider returned invalid metadata")
    return value
