from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentgraph.domain.distributed import NodeRole


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
    memory_enabled: bool = True
    memory_max_content_chars: int = Field(default=10_000, gt=0, le=100_000)
    memory_max_tags: int = Field(default=16, gt=0, le=100)
    memory_max_tag_chars: int = Field(default=64, gt=0, le=200)
    memory_max_results: int = Field(default=8, gt=0, le=50)
    memory_max_context_chars: int = Field(default=6_000, gt=0, le=100_000)
    tools_enabled: bool = False
    tool_approval_timeout_seconds: float = Field(default=120, gt=0, le=3600)
    tool_execution_timeout_seconds: float = Field(default=30, gt=0, le=300)
    tool_max_output_chars: int = Field(default=4_000, gt=0, le=20_000)
    tool_application_allowlist_json: str = "{}"
    lexi_max_tool_steps: int = Field(default=3, gt=0, le=10)
    orchestration_max_workers: int = Field(default=4, gt=0, le=20)
    orchestration_max_parallel: int = Field(default=2, gt=0, le=20)
    orchestration_max_depth: int = Field(default=2, ge=0, le=10)
    orchestration_child_timeout_seconds: float = Field(default=120, gt=0, le=3600)
    orchestration_max_context_chars: int = Field(default=24_000, gt=0, le=100_000)
    node_role: NodeRole = NodeRole.CORE
    core_url: str | None = None
    node_name: str = "AgentGraph Worker"
    node_id_path: str = "./data/worker-node-id"
    worker_enrollment_secret: str | None = None
    worker_enabled: bool = False
    worker_heartbeat_interval_seconds: float = Field(default=10, gt=0, le=300)
    worker_heartbeat_timeout_seconds: float = Field(default=30, gt=1, le=900)
    worker_max_connections: int = Field(default=32, gt=0, le=500)
    worker_max_tasks: int = Field(default=16, gt=0, le=100)
    worker_max_messages: int = Field(default=64, gt=0, le=1000)
    worker_reconnect_max_seconds: float = Field(default=30, gt=0, le=300)
    worker_task_timeout_seconds: float = Field(default=10, gt=0, le=60)
