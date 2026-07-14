from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class QueryFimEventsTool(BaseTool):
    name = "query_fim_events"
    description = "Consulta eventos de integridad de archivos (FIM) por accion de archivo y/o host."
    parameters = {
        "type": "object",
        "properties": {
            "file_action": {"type": "string", "description": "ej. modified|created|deleted"},
            "host": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": [],
    }

    def run(self, a: dict[str, Any]) -> Any:
        limit = min(int(a.get("limit", 50)), 200)
        filters: dict[str, Any] = {"category": "filesystem"}
        extra = {
            "file_action": a.get("file_action"),
            "host": a.get("host"),
        }
        filters.update({k: v for k, v in extra.items() if v is not None})
        events = self.ctx.store.query(filters=filters, limit=limit)
        return {"returned": len(events), "events": [slim_event(e) for e in events]}
