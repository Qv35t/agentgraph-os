import base64
import time

import httpx

from agentgraph.models.contracts import (
    ModelErrorCode,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelRouterError,
    ModelUsage,
    ProviderCapability,
    ProviderStatus,
)
from agentgraph.models.router import ModelProvider
from agentgraph.providers.validation import (
    optional_non_negative_int,
    optional_string,
    require_safe_base_url,
)


class OllamaProvider(ModelProvider):
    provider_id = "ollama"
    capabilities = ProviderCapability(
        chat=True,
        discovery=True,
        vision=True,
        image_captioning=True,
        ocr=True,
        grounding=True,
        ui_understanding=True,
        multi_image=True,
    )

    def __init__(self, client: httpx.AsyncClient, base_url: str = "http://127.0.0.1:11434") -> None:
        self._client = client
        self._base_url = require_safe_base_url(base_url, credentialed=False, loopback_only=True)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        model_id = request.model_ref.model_id
        started = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model_id,
                    "messages": [_message_json(message) for message in request.messages],
                    "stream": False,
                },
            )
            if response.status_code == 404:
                raise ModelRouterError(ModelErrorCode.MODEL_NOT_FOUND, "Requested model was not found")
            if response.status_code == 429:
                raise ModelRouterError(ModelErrorCode.RATE_LIMITED, "Ollama rate limit exceeded")
            response.raise_for_status()
            payload = response.json()
            content = payload["message"]["content"]
            if not isinstance(content, str):
                raise KeyError
        except ModelRouterError:
            raise
        except httpx.TimeoutException as error:
            raise ModelRouterError(ModelErrorCode.TIMEOUT, "Model request timed out") from error
        except httpx.HTTPError as error:
            raise ModelRouterError(ModelErrorCode.PROVIDER_UNAVAILABLE, "Ollama is unavailable") from error
        except (KeyError, TypeError, ValueError) as error:
            raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "Ollama returned an invalid response") from error
        input_tokens = optional_non_negative_int(payload.get("prompt_eval_count"))
        output_tokens = optional_non_negative_int(payload.get("eval_count"))
        total_tokens = (
            input_tokens + output_tokens if isinstance(input_tokens, int) and isinstance(output_tokens, int) else None
        )
        return ModelResponse(
            content=content,
            provider_id=self.provider_id,
            model_id=optional_string(payload.get("model")) or model_id,
            finish_reason=optional_string(payload.get("done_reason")),
            usage=ModelUsage(input_tokens, output_tokens, total_tokens),
            latency_ms=round((time.monotonic() - started) * 1000),
        )

    async def status(self) -> ProviderStatus:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
            models = tuple(item["name"] for item in payload["models"] if isinstance(item.get("name"), str))
            return ProviderStatus(self.provider_id, True, True, models)
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return ProviderStatus(
                self.provider_id,
                True,
                False,
                error_code=ModelErrorCode.PROVIDER_UNAVAILABLE,
                error="Ollama is unavailable",
            )


def _message_json(message: ModelMessage) -> dict[str, object]:
    payload: dict[str, object] = {"role": message.role, "content": message.content}
    if message.images:
        payload["images"] = [base64.b64encode(image.data).decode("ascii") for image in message.images]
    return payload
