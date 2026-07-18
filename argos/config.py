from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


def _load_dotenv() -> None:
    """Carga variables de entorno desde un archivo .env si existe (sin dependencias).
    Solo sobreescribe variables que aun no esten definidas en el entorno."""
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


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
    local_model_path: str = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    local_model_url: str = ""
    local_model_sha256: str = ""
    local_autoserve: bool = True
    local_server_bin: str = "llama-server"
    llm_mode: LlmMode = LlmMode.HYBRID
    request_timeout: float = 30.0
    anonymous_rate_limit_per_hour: int = 200
    retention_days: int = 90
    default_switch: SwitchLevel = SwitchLevel.OBSERVE
    default_switch_env: bool = False
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    agent_poll_interval: float = 5.0
    kilo_api_key: Optional[str] = None
    auth_secret: Optional[str] = None
    api_token: Optional[str] = None
    rate_limit_per_hour: int = 200
    cors_origins: list[str] = field(default_factory=list)
    require_auth: bool = True
    autonomy_enabled: bool = True
    autonomy_max_actions_per_hour: int = 10
    autonomy_host_cooldown_sec: int = 300
    remote_providers: list[RemoteProvider] = field(default_factory=list)
    agent_sources: list[str] = field(default_factory=lambda: [
        "process", "network", "logon", "persistence", "fim", "usb", "lotl", "kernel_exfil",
    ])
    fim_enabled: bool = True
    fim_paths: list[str] = field(default_factory=lambda: _default_fim_paths())
    realtime_enabled: bool = False
    realtime_interval: float = 1.0
    network_monitor_enabled: bool = False
    network_monitor_interval_ticks: int = 1
    network_monitor_ports: list[int] | None = None

    def model_dir(self) -> Path:
        return self.root / "models"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


def _default_fim_paths() -> list[str]:
    import os

    if os.name == "nt":
        root = os.environ.get("SystemRoot", r"C:\Windows")
        return [
            os.path.join(root, "System32", "drivers", "etc", "hosts"),
            os.path.join(root, "System32", "winevt", "Logs", "Security.evtx"),
        ]
    return ["/etc/passwd", "/etc/shadow", "/etc/ssh/sshd_config", "/etc/cron.d"]


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
    _load_dotenv()
    cfg = Config()
    cfg.kilo_api_key = os.environ.get("KILO_API_KEY")
    mode = os.environ.get("ARGOS_LLM_MODE")
    if mode:
        cfg.llm_mode = LlmMode(mode)
    if os.environ.get("ARGOS_LOCAL_BASE_URL"):
        cfg.local_base_url = os.environ["ARGOS_LOCAL_BASE_URL"]
    if os.environ.get("ARGOS_LOCAL_MODEL"):
        cfg.local_model = os.environ["ARGOS_LOCAL_MODEL"]
    if os.environ.get("ARGOS_LOCAL_MODEL_URL"):
        cfg.local_model_url = os.environ["ARGOS_LOCAL_MODEL_URL"]
    if os.environ.get("ARGOS_LOCAL_MODEL_SHA256"):
        cfg.local_model_sha256 = os.environ["ARGOS_LOCAL_MODEL_SHA256"]
    if os.environ.get("ARGOS_LOCAL_AUTOSERVE"):
        cfg.local_autoserve = os.environ["ARGOS_LOCAL_AUTOSERVE"].lower() not in ("0", "false", "no", "off")
    if os.environ.get("ARGOS_LOCAL_SERVER_BIN"):
        cfg.local_server_bin = os.environ["ARGOS_LOCAL_SERVER_BIN"]
    if os.environ.get("ARGOS_SERVER_HOST"):
        cfg.server_host = os.environ["ARGOS_SERVER_HOST"]
    if os.environ.get("ARGOS_SERVER_PORT"):
        cfg.server_port = int(os.environ["ARGOS_SERVER_PORT"])
    if os.environ.get("ARGOS_AUTH_SECRET"):
        cfg.auth_secret = os.environ["ARGOS_AUTH_SECRET"]
    if os.environ.get("ARGOS_API_TOKEN"):
        cfg.api_token = os.environ["ARGOS_API_TOKEN"]
    if os.environ.get("ARGOS_RATE_LIMIT_PER_HOUR"):
        cfg.rate_limit_per_hour = int(os.environ["ARGOS_RATE_LIMIT_PER_HOUR"])
    if os.environ.get("ARGOS_CORS_ORIGINS"):
        cfg.cors_origins = [o.strip() for o in os.environ["ARGOS_CORS_ORIGINS"].split(",") if o.strip()]
    if os.environ.get("ARGOS_REQUIRE_AUTH"):
        cfg.require_auth = os.environ["ARGOS_REQUIRE_AUTH"].lower() not in ("0", "false", "no", "off")
    if os.environ.get("ARGOS_AUTONOMY_ENABLED"):
        cfg.autonomy_enabled = os.environ["ARGOS_AUTONOMY_ENABLED"].lower() not in ("0", "false", "no", "off")
    if os.environ.get("ARGOS_AUTONOMY_MAX_ACTIONS_PER_HOUR"):
        cfg.autonomy_max_actions_per_hour = int(os.environ["ARGOS_AUTONOMY_MAX_ACTIONS_PER_HOUR"])
    if os.environ.get("ARGOS_AUTONOMY_HOST_COOLDOWN_SEC"):
        cfg.autonomy_host_cooldown_sec = int(os.environ["ARGOS_AUTONOMY_HOST_COOLDOWN_SEC"])
    if os.environ.get("ARGOS_DEFAULT_SWITCH"):
        try:
            cfg.default_switch = SwitchLevel(os.environ["ARGOS_DEFAULT_SWITCH"])
            cfg.default_switch_env = True
        except ValueError:
            cfg.default_switch = SwitchLevel.OBSERVE
    if os.environ.get("ARGOS_REALTIME_ENABLED"):
        cfg.realtime_enabled = os.environ["ARGOS_REALTIME_ENABLED"].lower() not in ("0", "false", "no", "off")
    if os.environ.get("ARGOS_AGENT_SOURCES"):
        cfg.agent_sources = [s.strip() for s in os.environ["ARGOS_AGENT_SOURCES"].split(",") if s.strip()]
    if os.environ.get("ARGOS_FIM_PATHS"):
        cfg.fim_paths = [p.strip() for p in os.environ["ARGOS_FIM_PATHS"].split(",") if p.strip()]
    cfg.remote_providers = _load_remote_providers(cfg)
    cfg.ensure_dirs()
    validate_config(cfg)
    return cfg


class ConfigError(ValueError):
    """La configuración es inválida y el servidor no debe arrancar."""


def validate_config(cfg: "Config") -> None:
    """Valida la config antes de arrancar; lanza ConfigError legible si falla."""
    if cfg.server_port < 1 or cfg.server_port > 65535:
        raise ConfigError(f"server_port fuera de rango: {cfg.server_port}")
    if cfg.agent_poll_interval <= 0:
        raise ConfigError(f"agent_poll_interval debe ser > 0: {cfg.agent_poll_interval}")
    if cfg.request_timeout <= 0:
        raise ConfigError(f"request_timeout debe ser > 0: {cfg.request_timeout}")
    if cfg.retention_days < 1:
        raise ConfigError(f"retention_days debe ser >= 1: {cfg.retention_days}")
    if cfg.rate_limit_per_hour < 1:
        raise ConfigError(f"rate_limit_per_hour debe ser >= 1: {cfg.rate_limit_per_hour}")
    try:
        cfg.llm_mode = LlmMode(cfg.llm_mode.value)
    except ValueError:
        raise ConfigError(f"llm_mode inválido: {cfg.llm_mode}")
    try:
        cfg.default_switch = SwitchLevel(cfg.default_switch.value)
    except ValueError:
        raise ConfigError(f"default_switch inválido: {cfg.default_switch}")
    # data_dir debe ser escribible
    try:
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        test = cfg.data_dir / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
    except Exception as exc:
        raise ConfigError(f"data_dir no es escribible ({cfg.data_dir}): {exc}") from exc
