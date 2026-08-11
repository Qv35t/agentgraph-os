import time
from dataclasses import asdict

import httpx

from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelRequest,
    ModelResponse,
    ModelRouterError,
    ModelUsage,
    ProviderStatus,
)
from agentgraph.models.router import ModelProvider
from agentgraph.providers.validation import (
    optional_non_negative_int,
    optional_string,
    require_safe_base_url,
)


class OpenAICompatibleProvider(ModelProvider):
    """Optional OpenAI-compatible transport; credentials stay in environment only."""

    def __init__(self, provider_id: str, client: httpx.AsyncClient, base_url: str, api_key: str | None = None) -> None:
        self.provider_id = provider_id
        self._client = client
        self._base_url = require_safe_base_url(base_url, credentialed=bool(api_key))
        self._api_key = api_key

    async def complete(self, request: ModelRequest) -> ModelResponse:
        model_id = request.model_ref.model_id
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        started = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model_id,
                    "messages": [asdict(message) for message in request.messages],
                },
            )
            if response.status_code == 401:
                raise ModelRouterError(ModelErrorCode.AUTHENTICATION_FAILED, "Provider authentication failed")
            if response.status_code == 404:
                raise ModelRouterError(ModelErrorCode.MODEL_NOT_FOUND, "Requested model was not found")
            if response.status_code == 429:
                raise ModelRouterError(ModelErrorCode.RATE_LIMITED, "Provider rate limit exceeded")
            response.raise_for_status()
            payload = response.json()
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise KeyError
        except ModelRouterError:
            raise
        except httpx.TimeoutException as error:
            raise ModelRouterError(ModelErrorCode.TIMEOUT, "Model request timed out") from error
        except httpx.HTTPError as error:
            raise ModelRouterError(ModelErrorCode.PROVIDER_UNAVAILABLE, "Provider is unavailable") from error
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "Provider returned an invalid response") from error
        usage = payload.get("usage", {})
        if not isinstance(usage, dict):
            raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "Provider returned invalid usage metadata")
        return ModelResponse(
            content=content,
            provider_id=self.provider_id,
            model_id=optional_string(payload.get("model")) or model_id,
            finish_reason=optional_string(choice.get("finish_reason")),
            usage=ModelUsage(
                optional_non_negative_int(usage.get("prompt_tokens")),
                optional_non_negative_int(usage.get("completion_tokens")),
                optional_non_negative_int(usage.get("total_tokens")),
            ),
            latency_ms=round((time.monotonic() - started) * 1000),
        )

    async def status(self) -> ProviderStatus:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            response = await self._client.get(f"{self._base_url}/models", headers=headers)
            if response.status_code == 401:
                return ProviderStatus(
                    self.provider_id,
                    True,
                    False,
                    error_code=ModelErrorCode.AUTHENTICATION_FAILED,
                    error="Provider authentication failed",
                )
            if response.status_code == 429:
                return ProviderStatus(
                    self.provider_id,
                    True,
                    False,
                    error_code=ModelErrorCode.RATE_LIMITED,
                    error="Provider rate limit exceeded",
                )
            response.raise_for_status()
            payload = response.json()
            models = tuple(item["id"] for item in payload["data"] if isinstance(item.get("id"), str))
            return ProviderStatus(self.provider_id, True, True, models)
        except httpx.TimeoutException:
            return ProviderStatus(
                self.provider_id,
                True,
                False,
                error_code=ModelErrorCode.TIMEOUT,
                error="Provider discovery timed out",
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return ProviderStatus(
                self.provider_id,
                True,
                False,
                error_code=ModelErrorCode.PROVIDER_UNAVAILABLE,
                error="Provider is unavailable",
            )
