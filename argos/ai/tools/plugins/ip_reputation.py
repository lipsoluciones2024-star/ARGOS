from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class IpReputationTool(BaseTool):
    name = "ip_reputation"
    description = "Consulta la reputacion de una IP en la inteligencia de amenazas local."
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {"ip": {"type": "string", "description": "IP a consultar"}},
        "required": ["ip"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        ip = str(a.get("ip", "")).strip()
        if not ip:
            return {"error": "ip requerida"}
        result = self.ctx.intel.lookup(ip)
        if not result or result.get("source") == "unknown":
            return {"ip": ip, "reputation": "unknown"}
        return {"ip": ip, **result}
