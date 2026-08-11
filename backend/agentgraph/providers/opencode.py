import asyncio
import time

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


class OpenCodeBridgeProvider(ModelProvider):
    provider_id = "opencode"

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        cleanup_timeout_seconds: float = 2,
    ) -> None:
        self._client = client
        self._base_url = require_safe_base_url(base_url, credentialed=bool(password), loopback_only=True)
        self._auth = httpx.BasicAuth(username or "opencode", password) if password else None
        self._cleanup_timeout_seconds = cleanup_timeout_seconds

    async def complete(self, request: ModelRequest) -> ModelResponse:
        model_id = request.model_ref.model_id
        provider_id, separator, provider_model_id = model_id.partition("/")
        if not separator:
            raise ModelRouterError(
                ModelErrorCode.CONFIGURATION_ERROR,
                "OpenCode model reference must include provider and model",
            )
        started = time.monotonic()
        session_id: str | None = None
        message_started = False
        try:
            session_response = await self._post(
                "/session",
                {
                    "title": "AgentGraph model transport",
                    "permission": [{"permission": "*", "pattern": "*", "action": "deny"}],
                },
            )
            self._raise_status(session_response)
            session_id = session_response.json()["id"]
            prompt = "\n\n".join(f"{message.role}: {message.content}" for message in request.messages)
            message_started = True
            response = await self._post(
                f"/session/{session_id}/message",
                {
                    "model": {"providerID": provider_id, "modelID": provider_model_id},
                    "tools": {"*": False},
                    "parts": [{"type": "text", "text": prompt}],
                },
            )
            self._raise_status(response)
            payload = response.json()
            if not isinstance(payload, dict):
                raise KeyError
            info = payload["info"]
            parts = payload["parts"]
            if not isinstance(info, dict) or not isinstance(parts, list):
                raise KeyError
            if any(not isinstance(part, dict) for part in parts):
                raise KeyError
            if info.get("error"):
                self._raise_message_error(info["error"])
            content = "".join(
                part["text"] for part in parts if part.get("type") == "text" and isinstance(part.get("text"), str)
            )
            if not content:
                raise KeyError
            tokens = info.get("tokens", {})
            if not isinstance(tokens, dict):
                raise KeyError
        except asyncio.CancelledError:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=True)
                session_id = None
            raise
        except ModelRouterError:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=message_started)
                session_id = None
            raise
        except httpx.TimeoutException as error:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=message_started)
                session_id = None
            raise ModelRouterError(ModelErrorCode.TIMEOUT, "OpenCode request timed out") from error
        except httpx.HTTPError as error:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=message_started)
                session_id = None
            raise ModelRouterError(ModelErrorCode.PROVIDER_UNAVAILABLE, "OpenCode is unavailable") from error
        except (KeyError, TypeError, ValueError) as error:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=message_started)
                session_id = None
            raise ModelRouterError(ModelErrorCode.INVALID_RESPONSE, "OpenCode returned an invalid response") from error
        finally:
            if session_id is not None:
                await self._shielded_cleanup(session_id, abort=False)
        return ModelResponse(
            content=content,
            provider_id=self.provider_id,
            model_id=f"{optional_string(info.get('providerID')) or provider_id}/"
            f"{optional_string(info.get('modelID')) or provider_model_id}",
            finish_reason=optional_string(info.get("finish")),
            usage=ModelUsage(
                optional_non_negative_int(tokens.get("input")),
                optional_non_negative_int(tokens.get("output")),
                optional_non_negative_int(tokens.get("total")),
            ),
            latency_ms=round((time.monotonic() - started) * 1000),
        )

    async def status(self) -> ProviderStatus:
        try:
            health = await self._get("/global/health")
            self._raise_status(health)
            response = await self._get("/config/providers")
            self._raise_status(response)
            models = tuple(
                f"{provider['id']}/{model_id}"
                for provider in response.json()["providers"]
                for model_id in provider.get("models", {})
            )
            return ProviderStatus(self.provider_id, True, True, models)
        except ModelRouterError as error:
            return ProviderStatus(self.provider_id, True, False, error_code=error.code, error=str(error))
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return ProviderStatus(
                self.provider_id,
                True,
                False,
                error_code=ModelErrorCode.PROVIDER_UNAVAILABLE,
                error="OpenCode is unavailable",
            )

    @staticmethod
    def _raise_status(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise ModelRouterError(ModelErrorCode.AUTHENTICATION_FAILED, "OpenCode authentication failed")
        if response.status_code == 404:
            raise ModelRouterError(ModelErrorCode.MODEL_NOT_FOUND, "OpenCode model was not found")
        if response.status_code == 429:
            raise ModelRouterError(ModelErrorCode.RATE_LIMITED, "OpenCode rate limit exceeded")
        response.raise_for_status()

    @staticmethod
    def _raise_message_error(error: object) -> None:
        error_data = error if isinstance(error, dict) else {}
        raw_nested_data = error_data.get("data")
        nested_data = raw_nested_data if isinstance(raw_nested_data, dict) else {}
        status_code = error_data.get("statusCode") or nested_data.get("statusCode")
        name = str(error_data.get("name", "")).lower()
        text = f"{name} {error}".lower()
        if status_code in {401, 403} or "auth" in text or "unauthorized" in text:
            code = ModelErrorCode.AUTHENTICATION_FAILED
        elif status_code == 429 or "rate" in text or "quota" in text:
            code = ModelErrorCode.RATE_LIMITED
        elif status_code == 404 or ("model" in text and "not" in text):
            code = ModelErrorCode.MODEL_NOT_FOUND
        elif "timeout" in text:
            code = ModelErrorCode.TIMEOUT
        elif "abort" in text or "cancel" in text:
            code = ModelErrorCode.CANCELLED
        else:
            code = ModelErrorCode.PROVIDER_UNAVAILABLE
        raise ModelRouterError(code, "OpenCode provider request failed")

    async def _shielded_cleanup(self, session_id: str, *, abort: bool) -> None:
        cleanup_task = asyncio.create_task(self._cleanup_session(session_id, abort=abort))
        try:
            await asyncio.shield(cleanup_task)
        except asyncio.CancelledError:
            await cleanup_task
            raise

    async def _cleanup_session(self, session_id: str, *, abort: bool) -> None:
        if abort:
            try:
                response = await asyncio.wait_for(
                    self._post(f"/session/{session_id}/abort", None),
                    timeout=self._cleanup_timeout_seconds,
                )
                response.raise_for_status()
            except (TimeoutError, httpx.HTTPError):
                pass
        try:
            response = await asyncio.wait_for(
                self._delete(f"/session/{session_id}"),
                timeout=self._cleanup_timeout_seconds,
            )
            response.raise_for_status()
        except (TimeoutError, httpx.HTTPError):
            pass

    async def _get(self, path: str) -> httpx.Response:
        if self._auth is None:
            return await self._client.get(f"{self._base_url}{path}")
        return await self._client.get(f"{self._base_url}{path}", auth=self._auth)

    async def _post(self, path: str, payload: dict[str, object] | None) -> httpx.Response:
        if self._auth is None:
            return await self._client.post(f"{self._base_url}{path}", json=payload)
        return await self._client.post(f"{self._base_url}{path}", json=payload, auth=self._auth)

    async def _delete(self, path: str) -> httpx.Response:
        if self._auth is None:
            return await self._client.delete(f"{self._base_url}{path}")
        return await self._client.delete(f"{self._base_url}{path}", auth=self._auth)
