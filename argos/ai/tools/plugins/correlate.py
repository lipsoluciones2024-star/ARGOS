from __future__ import annotations

from collections import Counter
from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool, slim_event


@register_tool
class CorrelateTool(BaseTool):
    name = "correlate"
    description = (
        "Correlaciona eventos, alertas e indicadores (IOC) para un host o IP: construye una "
        "linea de tiempo, tecnicas MITRE ATT&CK sospechosas, IOCs coincidentes y un veredicto. "
        "Analisis, no ejecuta acciones."
    )
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "host o IP a investigar"},
            "limit": {"type": "integer"},
        },
        "required": ["target"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        target = str(a.get("target", "")).strip()
        if not target:
            return {"error": "target requerido"}
        limit = int(a.get("limit", 200))
        is_ip = all(ch.isdigit() or ch == "." for ch in target) and target.count(".") == 3
        if is_ip:
            events = self.ctx.store.query(filters={"text": target}, limit=limit)
        else:
            events = self.ctx.store.query(filters={"host": target}, limit=limit)

        host_h = target.strip().lower()
        alerts = [
            al for al in self.ctx.engine.recent_alerts(limit=max(limit, 200))
            if str(al.get("host", "")).strip().lower() == host_h
            or (is_ip and target in str(al))
        ]

        techniques: Counter[str] = Counter()
        categories: Counter[str] = Counter()
        iocs: list[dict[str, Any]] = []
        seen_ioc: set[str] = set()
        for e in events:
            if e.attack_id:
                techniques[e.attack_id] += 1
            if e.category:
                categories[e.category] += 1
            for ip in (e.src_ip, e.dst_ip):
                if ip and ip not in seen_ioc:
                    seen_ioc.add(ip)
                    res = self.ctx.intel.lookup(ip)
                    if res.get("malicious"):
                        iocs.append({"ip": ip, **res})

        verdict = "benigno"
        if iocs:
            verdict = "malicioso (IOC conocido)"
        elif alerts:
            sev = {al.get("severity") for al in alerts}
            if "critical" in sev or "high" in sev:
                verdict = "alta probabilidad de compromiso"
            else:
                verdict = "actividad sospechosa"
        elif techniques:
            verdict = "actividad con tecnicas ATT&CK observadas"

        return {
            "target": target,
            "is_ip": is_ip,
            "event_count": len(events),
            "alert_count": len(alerts),
            "verdict": verdict,
            "techniques": dict(techniques),
            "categories": dict(categories),
            "matched_iocs": iocs,
            "alerts": alerts[:20],
            "timeline": [slim_event(e) for e in events[:50]],
        }
