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
