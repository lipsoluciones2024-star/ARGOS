from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool
from argos.scan import network as net_scan


@register_tool
class NetworkReconTool(BaseTool):
    name = "network_recon"
    description = (
        "Reconocimiento de red en tiempo real sobre un objetivo: portscan TCP, ping, "
        "traceroute, resolucion DNS y WHOIS. Usa comandos del SO (ping/tracert/whois) y "
        "sockets; nmap opcional si esta instalado. Solo lectura/analisis."
    )
    perm = "analyze"
    parameters = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "IP o hostname a analizar"},
            "kinds": {
                "type": "array",
                "items": {"type": "string", "enum": ["portscan", "ping", "traceroute", "dns", "whois", "nmap"]},
            },
            "ports": {"type": "array", "items": {"type": "integer"}},
            "timeout": {"type": "number"},
        },
        "required": ["target"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        target = str(a.get("target", "")).strip()
        if not target:
            return {"error": "target requerido"}
        kinds = a.get("kinds") or ["portscan", "ping", "dns"]
        ports = a.get("ports")
        timeout = float(a.get("timeout", 1.0))
        try:
            return net_scan.network_scan(target, kinds=kinds, ports=ports, timeout=timeout)
        except Exception as exc:
            return {"error": str(exc)}
