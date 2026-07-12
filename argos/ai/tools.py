from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from argos.ai.privacy import guard_privacy
from argos.detection.engine import DetectionEngine
from argos.detection.threat_intel import ThreatIntel
from argos.storage.store import EventStore

ALLOWED_TOOLS = {
    "query_events",
    "get_process_tree",
    "get_active_connections",
    "list_alerts",
    "lookup_ioc",
    "explain_attck_technique",
}


@dataclass
class ToolResult:
    name: str
    output: Any


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "query_events",
                "description": "Consulta eventos OCSF almacenados con filtros (category, host, severity, attack_id, text, since).",
                "parameters": {
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
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_process_tree",
                "description": "Obtiene eventos de proceso (arbol) filtrando por PID o todos los recientes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pid": {"type": "integer", "description": "PID a inspeccionar (opcional)"},
                        "limit": {"type": "integer", "default": 100},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_active_connections",
                "description": "Lista conexiones de red activas registradas.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_alerts",
                "description": "Lista alertas de deteccion por severidad.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "description": "high|critical|medium|low|info"},
                        "limit": {"type": "integer", "default": 50},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_ioc",
                "description": "Busca un indicador de compromiso (IP, dominio, hash) en threat intel.",
                "parameters": {
                    "type": "object",
                    "properties": {"indicator": {"type": "string"}},
                    "required": ["indicator"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "explain_attck_technique",
                "description": "Explica una tecnica MITRE ATT&CK por su ID (ej. T1059.001).",
                "parameters": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
            },
        },
    ]


class ToolExecutor:
    def __init__(self, store: EventStore, engine: DetectionEngine, intel: ThreatIntel) -> None:
        self.store = store
        self.engine = engine
        self.intel = intel

    def validate(self, name: str) -> bool:
        return name in ALLOWED_TOOLS

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if not self.validate(name):
            return ToolResult(name=name, output={"error": f"tool '{name}' not allowed"})
        handler: dict[str, Callable[[dict[str, Any]], Any]] = {
            "query_events": self._query_events,
            "get_process_tree": self._process_tree,
            "get_active_connections": self._connections,
            "list_alerts": self._list_alerts,
            "lookup_ioc": self._lookup_ioc,
            "explain_attck_technique": self._explain,
        }
        try:
            out = handler[name](arguments or {})
        except Exception as exc:
            out = {"error": str(exc)}
        if isinstance(out, str):
            out = guard_privacy(out)
        return ToolResult(name=name, output=out)

    @staticmethod
    def _slim(e: "Any") -> dict:
        d = e.as_dict()
        return {
            "time": d.get("time"),
            "category": d.get("category"),
            "host": d.get("host"),
            "severity": d.get("severity"),
            "process_name": d.get("process_name"),
            "process_cmdline": (d.get("process_cmdline") or "")[:160],
            "src_ip": d.get("src_ip"),
            "dst_ip": d.get("dst_ip"),
            "attack_id": d.get("attack_id"),
        }

    def _query_events(self, a: dict) -> Any:
        limit = min(int(a.get("limit", 20)), 50)
        events = self.store.query(
            filters={k: a[k] for k in ("category", "host", "severity", "attack_id", "text", "since") if a.get(k) is not None},
            limit=limit,
        )
        return {
            "total_events": self.store.count(),
            "returned": len(events),
            "note": "payload limitado a campos clave; usa filtros para acotar",
            "events": [self._slim(e) for e in events],
        }

    def _process_tree(self, a: dict) -> Any:
        pid = a.get("pid")
        events = self.store.process_tree(int(pid) if pid is not None else None)
        return {"returned": len(events), "events": [self._slim(e) for e in events]}

    def _connections(self, a: dict) -> Any:
        events = self.store.active_connections()
        return {"returned": len(events), "events": [self._slim(e) for e in events]}

    def _list_alerts(self, a: dict) -> Any:
        alerts = self.engine.recent_alerts(limit=int(a.get("limit", 50)),
                                           severity=a.get("severity"))
        return {"returned": len(alerts), "alerts": alerts}

    def _lookup_ioc(self, a: dict) -> Any:
        return self.intel.lookup(str(a.get("indicator", "")))

    def _explain(self, a: dict) -> Any:
        from argos.detection.attack import AttackMapper

        tid = str(a.get("id", "")).upper()
        mapper = AttackMapper()
        name = mapper.technique_name(tid)
        return {"id": tid, "name": name or "unknown", "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"}
