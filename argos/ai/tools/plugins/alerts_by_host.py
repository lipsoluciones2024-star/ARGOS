from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class AlertsByHostTool(BaseTool):
    name = "alerts_by_host"
    description = "Lista las alertas de deteccion asociadas a un host especifico."
    parameters = {
        "type": "object",
        "properties": {"host": {"type": "string"}},
        "required": ["host"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        host = str(a.get("host", "")).strip().lower()
        if not host:
            return {"error": "host requerido"}
        alerts = [
            al for al in self.ctx.engine.recent_alerts(limit=200)
            if str(al.get("host", "")).strip().lower() == host
        ]
        return {"host": host, "returned": len(alerts), "alerts": alerts}
