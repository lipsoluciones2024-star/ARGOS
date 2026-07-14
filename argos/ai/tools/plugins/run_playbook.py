from __future__ import annotations

from collections import Counter
from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class RunPlaybookTool(BaseTool):
    name = "run_playbook"
    description = (
        "Ejecuta un playbook de respuesta: 'host_investigation' (detalle + alertas + "
        "eventos recientes de un host) o 'ioc_check' (reputacion de una IP)."
    )
    perm = "execute"
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": ["host_investigation", "ioc_check"]},
            "host": {"type": "string"},
            "ip": {"type": "string"},
        },
        "required": ["name"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        name = str(a.get("name", "")).strip().lower()
        if name == "host_investigation":
            host = str(a.get("host", "")).strip()
            if not host:
                return {"error": "host requerido para host_investigation"}
            events = self.ctx.store.query(filters={"host": host}, limit=50)
            categories: Counter[str] = Counter()
            procs: Counter[str] = Counter()
            for e in events:
                if e.category:
                    categories[e.category] += 1
                if e.process_name:
                    procs[e.process_name] += 1
            host_h = host.strip().lower()
            alerts = [
                al for al in self.ctx.engine.recent_alerts(limit=200)
                if str(al.get("host", "")).strip().lower() == host_h
            ]
            return {
                "playbook": "host_investigation",
                "host": host,
                "event_count": len(events),
                "categories": dict(categories),
                "top_processes": [
                    {"process_name": n, "count": c} for n, c in procs.most_common(10)
                ],
                "recent_events": [slim_event(e) for e in events[:20]],
                "alerts": alerts,
            }
        if name == "ioc_check":
            ip = str(a.get("ip", "")).strip()
            if not ip:
                return {"error": "ip requerido para ioc_check"}
            return {"playbook": "ioc_check", "ip": ip,
                    "reputation": self.ctx.intel.lookup(ip)}
        return {"error": f"playbook desconocido: {name}"}
