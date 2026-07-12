from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class LlmMode(str, Enum):
    HYBRID = "hybrid"
    REMOTE = "remote"
    LOCAL = "local"


class SwitchLevel(str, Enum):
    OBSERVE = "OBSERVE"
    SUGGEST = "SUGGEST"
    SEMI_AUTO = "SEMI-AUTO"
    FULL_AUTO = "FULL-AUTO"


@dataclass
class RemoteProvider:
    name: str
    base_url: str
    model: str
    api_key_env: Optional[str] = None
    requires_key: bool = False


@dataclass
class Config:
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    gateway_base_url: str = "https://api.kilo.ai/api/gateway"
    local_base_url: str = "http://127.0.0.1:8080/v1"
    local_model: str = "local-gguf"
    local_model_path: str = "models/qwen25-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    llm_mode: LlmMode = LlmMode.HYBRID
    request_timeout: float = 30.0
    anonymous_rate_limit_per_hour: int = 200
    retention_days: int = 90
    default_switch: SwitchLevel = SwitchLevel.OBSERVE
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    agent_poll_interval: float = 5.0
    kilo_api_key: Optional[str] = None
    remote_providers: list[RemoteProvider] = field(default_factory=list)

    def model_dir(self) -> Path:
        return self.root / "models"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


def _load_remote_providers(cfg: Config) -> list[RemoteProvider]:
    return [
        RemoteProvider(name="cerebras", base_url="https://api.cerebras.ai/v1",
                        model=os.environ.get("ARGOS_CEREBRAS_MODEL", "llama-4-scout"),
                        api_key_env="CEREBRAS_API_KEY", requires_key=True),
        RemoteProvider(name="groq", base_url="https://api.groq.com/openai/v1",
                        model=os.environ.get("ARGOS_GROQ_MODEL", "llama-3.3-70b-versatile"),
                        api_key_env="GROQ_API_KEY", requires_key=True),
        RemoteProvider(name="openrouter", base_url="https://openrouter.ai/api/v1",
                        model=os.environ.get("ARGOS_OPENROUTER_MODEL", "openai/gpt-oss-120b:free"),
                        api_key_env="OPENROUTER_API_KEY", requires_key=False),
    ]


def load_config() -> Config:
    cfg = Config()
    cfg.kilo_api_key = os.environ.get("KILO_API_KEY")
    mode = os.environ.get("ARGOS_LLM_MODE")
    if mode:
        cfg.llm_mode = LlmMode(mode)
    if os.environ.get("ARGOS_LOCAL_BASE_URL"):
        cfg.local_base_url = os.environ["ARGOS_LOCAL_BASE_URL"]
    if os.environ.get("ARGOS_LOCAL_MODEL"):
        cfg.local_model = os.environ["ARGOS_LOCAL_MODEL"]
    if os.environ.get("ARGOS_LOCAL_MODEL_PATH"):
        cfg.local_model_path = os.environ["ARGOS_LOCAL_MODEL_PATH"]
    if os.environ.get("ARGOS_SERVER_HOST"):
        cfg.server_host = os.environ["ARGOS_SERVER_HOST"]
    if os.environ.get("ARGOS_SERVER_PORT"):
        cfg.server_port = int(os.environ["ARGOS_SERVER_PORT"])
    cfg.remote_providers = _load_remote_providers(cfg)
    cfg.ensure_dirs()
    return cfg
