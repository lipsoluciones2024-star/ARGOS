from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class GetActiveConnectionsTool(BaseTool):
    name = "get_active_connections"
    description = "Lista conexiones de red activas registradas."
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, a: dict[str, Any]) -> Any:
        events = self.ctx.store.active_connections()
        return {"returned": len(events), "events": [slim_event(e) for e in events]}
