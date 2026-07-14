from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class QueryEventsTool(BaseTool):
    name = "query_events"
    description = (
        "Consulta eventos OCSF almacenados con filtros "
        "(category, host, severity, attack_id, text, since)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "process|network|filesystem|persistence|identity|kernel|memory|lotl|usb|exfil"},
            "host": {"type": "string"},
            "severity": {"type": "string"},
            "attack_id": {"type": "string"},
            "text": {"type": "string", "description": "busqueda full-text"},
            "since": {"type": "string", "description": "ISO timestamp desde cuando"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": [],
    }

    def run(self, a: dict[str, Any]) -> Any:
        limit = min(int(a.get("limit", 20)), 50)
        events = self.ctx.store.query(
            filters={k: a[k] for k in ("category", "host", "severity", "attack_id", "text", "since") if a.get(k) is not None},
            limit=limit,
        )
        return {
            "total_events": self.ctx.store.count(),
            "returned": len(events),
            "note": "payload limitado a campos clave; usa filtros para acotar",
            "events": [slim_event(e) for e in events],
        }
