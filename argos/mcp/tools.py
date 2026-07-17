from __future__ import annotations

from typing import Any, Dict, List, Optional

from argos.ai.tools.registry import _REGISTRY, ToolExecutor


class ToolAdapter:
    """Adapta una herramienta del nucleo ARGOS al formato MCP."""

    def __init__(self, name: str) -> None:
        self.name = name
        cls = _REGISTRY.get(name)
        self._cls = cls
        self.description = cls.description if cls else f"Tool {name}"
        self.input_schema = cls.parameters if cls else {"type": "object", "properties": {}}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def execute(self, executor: ToolExecutor, arguments: Dict[str, Any], role: str = "admin") -> Any:
        result = executor.execute(self.name, arguments or {}, role=role)
        return result.output


class MCPToolRegistry:
    """Registry de tools MCP basado en el registro de tools del nucleo."""

    def __init__(self, executor: Optional[ToolExecutor] = None) -> None:
        self.executor = executor
        self._adapters: Dict[str, ToolAdapter] = {}
        for name in _REGISTRY:
            self._adapters[name] = ToolAdapter(name)

    def set_executor(self, executor: ToolExecutor) -> None:
        self.executor = executor

    def list_tools(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._adapters.values()]

    def list_resources(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": "argos://events/recent",
                "name": "Recent Events",
                "description": "Eventos de seguridad mas recientes",
                "mimeType": "application/json",
            },
            {
                "uri": "argos://alerts/active",
                "name": "Active Alerts",
                "description": "Alertas activas",
                "mimeType": "application/json",
            },
        ]

    def list_prompts(self) -> List[Dict[str, Any]]:
        return [
            {"name": "analyze_event", "description": "Analiza un evento de seguridad"},
            {"name": "correlate_events", "description": "Correlaciona eventos en cadenas de ataque"},
        ]

    def execute_tool(self, name: str, arguments: Dict[str, Any], role: str = "admin") -> Any:
        if self.executor is None:
            raise RuntimeError("MCP executor no inicializado")
        if name not in self._adapters:
            raise ValueError(f"Tool no encontrada: {name}")
        return self._adapters[name].execute(self.executor, arguments, role=role)
