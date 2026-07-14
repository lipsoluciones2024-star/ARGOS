from __future__ import annotations

from collections import Counter
from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class GetHostDetailTool(BaseTool):
    name = "get_host_detail"
    description = "Detalla un host: total de eventos, conteo por categoria, procesos top y eventos recientes."
    parameters = {
        "type": "object",
        "properties": {"host": {"type": "string", "description": "nombre del host"}},
        "required": ["host"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        host = str(a.get("host", "")).strip()
        if not host:
            return {"error": "host requerido"}
        events = self.ctx.store.query(filters={"host": host}, limit=2000)
        categories: Counter[str] = Counter()
        procs: Counter[str] = Counter()
        for e in events:
            if e.category:
                categories[e.category] += 1
            if e.process_name:
                procs[e.process_name] += 1
        top_processes = [
            {"process_name": name, "count": c}
            for name, c in procs.most_common(10)
        ]
        return {
            "host": host,
            "event_count": len(events),
            "categories": dict(categories),
            "top_processes": top_processes,
            "recent_events": [slim_event(e) for e in events[:20]],
        }
