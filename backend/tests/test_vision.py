import time
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from agentgraph.app import create_app
from agentgraph.models.contracts import ModelRequest, ModelResponse, ProviderCapability, ProviderStatus
from agentgraph.models.router import ModelProvider, ModelRouter
from agentgraph.runtime.graph import DeterministicGraphRuntime
from agentgraph.settings import Settings

from .conftest import seed_test_session


class VisionProvider(ModelProvider):
    provider_id = "ollama"
    capabilities = ProviderCapability(vision=True, image_captioning=True, ocr=True, multi_image=True)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        assert request.messages[0].images
        return ModelResponse("visible text", "ollama", request.model_ref.model_id, latency_ms=1)

    async def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, True, True, ("vision-model",))


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_vision_upload_analysis_and_folder_policy(settings: Settings, tmp_path: Path) -> None:
    configured = settings.model_copy(
        update={
            "vision_enabled": True,
            "vision_storage_root": str(tmp_path / "storage"),
            "vision_allowed_roots": f'["{tmp_path}"]',
            "remote_control_enabled": True,
            "remote_control_policies": '{"vision-user":["read","execute","control"]}',
        }
    )
    router = ModelRouter({"ollama": VisionProvider()}, "ollama://vision-model")
    with TestClient(create_app(configured, DeterministicGraphRuntime(), router)) as client:
        seed_test_session(client, configured)
        uploaded = client.post(
            "/api/v1/vision/assets", files={"file": ("sample.png", _png(), "image/png")}
        )
        assert uploaded.status_code == 201
        asset_id = uploaded.json()["id"]

        invalid = client.post(
            "/api/v1/vision/assets", files={"file": ("bad.png", b"not-image", "image/png")}
        )
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "vision_invalid_image"

        analysis = client.post(f"/api/v1/vision/assets/{asset_id}/analyses", json={"mode": "ocr"})
        assert analysis.status_code == 202
        analysis_id = analysis.json()["id"]

        deadline = time.monotonic() + 1
        result = client.get(f"/api/v1/vision/analyses/{analysis_id}")
        while result.json()["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.01)
            result = client.get(f"/api/v1/vision/analyses/{analysis_id}")
        assert result.status_code == 200
        assert result.json()["status"] == "completed"
        assert result.json()["ocr_text"] == "visible text"

        forbidden = client.post(
            "/api/v1/vision/folders", json={"display_name": "Bad", "root": "/etc"}
        )
        assert forbidden.status_code == 403
