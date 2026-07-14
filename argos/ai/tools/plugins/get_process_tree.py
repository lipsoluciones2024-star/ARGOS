from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class GetProcessTreeTool(BaseTool):
    name = "get_process_tree"
    description = "Obtiene eventos de proceso (arbol) filtrando por PID o todos los recientes."
    parameters = {
        "type": "object",
        "properties": {
            "pid": {"type": "integer", "description": "PID a inspeccionar (opcional)"},
            "limit": {"type": "integer", "default": 100},
        },
        "required": [],
    }

    def run(self, a: dict[str, Any]) -> Any:
        pid = a.get("pid")
        events = self.ctx.store.process_tree(int(pid) if pid is not None else None)
        return {"returned": len(events), "events": [slim_event(e) for e in events]}
