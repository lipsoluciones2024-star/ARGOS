from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class GetHostsTool(BaseTool):
    name = "get_hosts"
    description = "Lista los hosts observados con su numero de eventos y ultimo avistamiento."
    parameters = {
        "type": "object",
        "properties": {"limit": {"type": "integer", "default": 50, "description": "max 200"}},
        "required": [],
    }

    def run(self, a: dict[str, Any]) -> Any:
        limit = min(int(a.get("limit", 50)), 200)
        return {"returned": limit, "hosts": self.ctx.store.hosts(limit=limit)}
