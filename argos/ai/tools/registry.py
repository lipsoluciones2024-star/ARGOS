from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Optional, Type

from argos.ai.privacy import guard_privacy
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.storage.store import EventStore

if TYPE_CHECKING:
    from argos.response.orchestrator import ResponseOrchestrator

# Taxonomía de permisos mínimos por herramienta (Cyber Brain · Tool Gateway).
# - read:    solo lectura de datos observados.
# - analyze: enriquecimiento / análisis (intel, ATT&CK, cobertura).
# - execute: acciones que afectan sistemas (pasan por el switch de autonomía).
# - modify:  cambian el estado de ARGOS (notificar, revertir, playbooks).
PERMISSIONS = ("read", "analyze", "execute", "modify")

# Rol -> permisos concedidos. operator tiene permisos mínimos; admin, todos.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "operator": {"read", "analyze"},
    "admin": {"read", "analyze", "execute", "modify"},
}


def role_can(role: str, perm: str) -> bool:
    """True si `role` tiene concedido el permiso `perm`."""
    if perm not in PERMISSIONS:
        return False
    return perm in ROLE_PERMISSIONS.get(role, set())


_REGISTRY: dict[str, Type["BaseTool"]] = {}


ALLOWED_TOOLS: set[str] = set()


def register_tool(cls: Type["BaseTool"]) -> Type["BaseTool"]:
    if not cls.name:
        raise ValueError(f"Tool {cls.__name__} must define a non-empty 'name'")
    _REGISTRY[cls.name] = cls
    return cls


class BaseTool:
    name: str = ""
    description: str = ""
    # Permiso mínimo requerido para invocar la herramienta (ver PERMISSIONS).
    perm: str = "read"
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    def __init__(self, ctx: "ToolContext") -> None:
        self.ctx = ctx

    def run(self, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError


@dataclass
class ToolContext:
    store: EventStore
    engine: DetectionEngine
    intel: ThreatIntel
    response: Optional["ResponseOrchestrator"] = None


@dataclass
class ToolResult:
    name: str
    output: Any


def slim_event(e: Any) -> dict:
    d = e.as_dict()
    return {
        "time": d.get("time"),
        "category": d.get("category"),
        "host": d.get("host"),
        "severity": d.get("severity"),
        "process_name": d.get("process_name"),
        "process_cmdline": (d.get("process_cmdline") or "")[:160],
        "src_ip": d.get("src_ip"),
        "dst_ip": d.get("dst_ip"),
        "attack_id": d.get("attack_id"),
    }


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": cls.description,
                "parameters": cls.parameters,
            },
        }
        for name, cls in _REGISTRY.items()
    ]


def discover_tools(package: str = "argos.ai.tools.plugins") -> None:
    try:
        mod = import_module(package)
    except ModuleNotFoundError:
        return
    pkg_path = getattr(mod, "__path__", None)
    if not pkg_path:
        return
    import pkgutil

    for info in pkgutil.iter_modules(list(pkg_path)):
        import_module(f"{package}.{info.name}")
    ALLOWED_TOOLS.clear()
    ALLOWED_TOOLS.update(_REGISTRY.keys())


class ToolExecutor:
    def __init__(
        self,
        store: EventStore,
        engine: DetectionEngine,
        intel: ThreatIntel,
        response: Optional["ResponseOrchestrator"] = None,
    ) -> None:
        self.ctx = ToolContext(store=store, engine=engine, intel=intel, response=response)

    def validate(self, name: str) -> bool:
        return name in _REGISTRY

    def can_run(self, name: str, role: str = "admin") -> bool:
        """True si la herramienta existe y `role` tiene su permiso concedido."""
        cls = _REGISTRY.get(name)
        if cls is None:
            return False
        return role_can(role, cls.perm)

    def execute(self, name: str, arguments: dict[str, Any], role: str = "admin") -> ToolResult:
        if name not in _REGISTRY:
            return ToolResult(name=name, output={"error": f"tool '{name}' not allowed"})
        cls = _REGISTRY[name]
        if not role_can(role, cls.perm):
            return ToolResult(
                name=name,
                output={"error": f"permiso '{cls.perm}' no concedido al rol '{role}'"},
            )
        try:
            out = cls(self.ctx).run(arguments or {})
        except Exception as exc:
            out = {"error": str(exc)}
        if isinstance(out, str):
            out = guard_privacy(out)
        return ToolResult(name=name, output=out)
