from collections.abc import Mapping
from dataclasses import replace

from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelMessage,
    ModelRef,
    ModelRequest,
    ModelResponse,
    ModelRouterError,
    ProviderCapability,
    ProviderStatus,
)


class ModelProvider:
    provider_id: str
    capabilities = ProviderCapability()

    async def complete(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    async def status(self) -> ProviderStatus:
        raise NotImplementedError


class DisabledProvider(ModelProvider):
    capabilities = ProviderCapability(chat=False, discovery=False)

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    async def complete(self, request: ModelRequest) -> ModelResponse:
        del request
        raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Provider is disabled")

    async def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, False, False)


class ProviderRegistry:
    def __init__(self, providers: Mapping[str, ModelProvider]) -> None:
        self._providers = dict(providers)

    def get(self, provider_id: str) -> ModelProvider | None:
        return self._providers.get(provider_id)

    def values(self) -> list[ModelProvider]:
        return list(self._providers.values())


class ModelRouter:
    def __init__(self, providers: Mapping[str, ModelProvider], default_model_ref: str) -> None:
        self._registry = ProviderRegistry(providers)
        self._default = ModelRef.parse(default_model_ref)

    async def complete(self, model_ref: str, messages: list[ModelMessage]) -> ModelResponse:
        reference = self._resolve_compatibility(model_ref)
        if reference.provider == "auto" and reference.model_id == "default":
            reference = self._default
        provider = self._registry.get(reference.provider)
        if provider is None:
            raise ModelRouterError(ModelErrorCode.PROVIDER_UNAVAILABLE, "Requested provider is unavailable")
        if not provider.capabilities.chat:
            raise ModelRouterError(ModelErrorCode.CONFIGURATION_ERROR, "Provider does not support chat")
        if any(message.images for message in messages) and not provider.capabilities.vision:
            raise ModelRouterError(ModelErrorCode.VISION_CAPABILITY_MISSING, "Provider does not support vision")
        request = ModelRequest(model_ref=reference, messages=tuple(messages))
        return await provider.complete(request)

    async def provider_statuses(self) -> list[ProviderStatus]:
        statuses = []
        for provider in self._registry.values():
            status = await provider.status()
            models = status.models if provider.capabilities.discovery else ()
            statuses.append(replace(status, models=models, capabilities=provider.capabilities))
        return statuses

    @staticmethod
    def _resolve_compatibility(value: str) -> ModelRef:
        compatibility = {
            "local/default": "auto://default",
            "qwen3-4b-nothink:latest": "ollama://qwen3-4b-nothink:latest",
            "qwen3:4B": "ollama://qwen3:4B",
            "qwen3:0.6B": "ollama://qwen3:0.6B",
        }
        return ModelRef.parse(compatibility.get(value, value))
