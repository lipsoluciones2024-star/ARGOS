from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class ListAlertsTool(BaseTool):
    name = "list_alerts"
    description = "Lista alertas de deteccion por severidad."
    parameters = {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "description": "high|critical|medium|low|info"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": [],
    }

    def run(self, a: dict[str, Any]) -> Any:
        alerts = self.ctx.engine.recent_alerts(
            limit=int(a.get("limit", 50)),
            severity=a.get("severity"),
        )
        return {"returned": len(alerts), "alerts": alerts}
