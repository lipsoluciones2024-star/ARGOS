from __future__ import annotations

import platform
import subprocess
from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


def _remove_firewall_block(cfg: Any, ip: str) -> dict[str, Any]:
    try:
        if platform.system() == "Windows":
            r = subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 "name=ARGOS_BLOCK", f"remoteip={ip}"],
                capture_output=True, text=True, timeout=30,
            )
            return {"removed": ip, "rc": r.returncode,
                    "stdout": r.stdout[:2000], "stderr": r.stderr[:2000]}
        r = subprocess.run(
            ["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"],
            capture_output=True, text=True, timeout=30,
        )
        return {"removed": ip, "rc": r.returncode,
                "stdout": r.stdout[:2000], "stderr": r.stderr[:2000]}
    except Exception as exc:
        return {"removed": ip, "error": str(exc)}


@register_tool
class UndoActionTool(BaseTool):
    name = "undo_action"
    description = "Revierte una accion de respuesta previa (actualmente soporta block_ip)."
    perm = "modify"
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "tipo de accion a revertir"},
            "target": {"type": "string", "description": "objetivo de la accion (ej. IP)"},
        },
        "required": ["action", "target"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        action = str(a.get("action", "")).strip().lower()
        target = str(a.get("target", "")).strip()
        if not action or not target:
            return {"error": "action y target requeridos"}
        if action == "block_ip":
            resp = self.ctx.response
            if resp is None:
                return {"error": "response unavailable"}
            return _remove_firewall_block(resp.cfg, target)
        return {"status": "unsupported", "action": action,
                "note": "manual revert may be required for this action type"}
