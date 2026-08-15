from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with local-safe defaults."""

    model_config = SettingsConfigDict(env_prefix="AGENTGRAPH_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./agentgraph.db"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    runtime_delay_seconds: float = Field(default=0, ge=0, le=60)
    cancellation_timeout_seconds: float = Field(default=5, gt=0, le=60)
    ollama_base_url: str = "http://127.0.0.1:11434"
    opencode_base_url: str | None = None
    opencode_basic_auth_username: str | None = None
    opencode_basic_auth_password: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    project_id: str = "project_local"
    remote_control_enabled: bool = False
    remote_control_policies: str = "{}"
    legacy_api_enabled: bool = False
    vision_enabled: bool = False
    vision_provider: str = "ollama"
    vision_model: str = "hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M"
    vision_allowed_roots: str = "[]"
    vision_storage_root: str = "./data/vision"
    vision_max_file_size_bytes: int = Field(default=10_000_000, gt=0, le=100_000_000)
    vision_max_image_pixels: int = Field(default=40_000_000, gt=0, le=100_000_000)
    vision_max_queue: int = Field(default=10, gt=0, le=100)
    vision_max_scan_files: int = Field(default=1_000, gt=0, le=10_000)
