import re
from dataclasses import dataclass, field
from enum import StrEnum


class ModelErrorCode(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    MODEL_NOT_FOUND = "model_not_found"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    INVALID_RESPONSE = "invalid_response"
    CONFIGURATION_ERROR = "configuration_error"
    VISION_CAPABILITY_MISSING = "vision_capability_missing"


class ModelRouterError(Exception):
    def __init__(self, code: ModelErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ModelRef:
    provider: str
    model_id: str

    @classmethod
    def parse(cls, value: str) -> "ModelRef":
        provider, separator, model_id = value.partition("://")
        if not separator or not provider or not model_id:
            raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Invalid model reference")
        if provider not in {"auto", "ollama", "opencode", "openrouter"}:
            raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Unsupported model provider")
        if provider == "auto" and model_id != "default":
            raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Unsupported automatic model reference")
        if not re.fullmatch(r"[A-Za-z0-9._:/-]+", model_id) or "://" in model_id:
            raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Invalid model identifier")
        return cls(provider=provider, model_id=model_id)


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: str
    content: str
    images: tuple["ImagePart", ...] = ()


@dataclass(frozen=True, slots=True)
class ImagePart:
    data: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ModelRequest:
    model_ref: ModelRef
    messages: tuple[ModelMessage, ...]


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    chat: bool = True
    discovery: bool = True
    vision: bool = False
    image_captioning: bool = False
    ocr: bool = False
    grounding: bool = False
    ui_understanding: bool = False
    multi_image: bool = False
    function_calling: bool = False


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    provider_id: str
    model_id: str
    finish_reason: str | None = None
    usage: ModelUsage = field(default_factory=ModelUsage)
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider_id: str
    enabled: bool
    available: bool
    models: tuple[str, ...] = ()
    capabilities: ProviderCapability = field(default_factory=ProviderCapability)
    error_code: ModelErrorCode | None = None
    error: str | None = None
