from __future__ import annotations

from typing import Any

from argos.ai.tools.registry import BaseTool, register_tool


@register_tool
class NotifyTool(BaseTool):
    name = "notify"
    description = "Informa al operador mediante la consola del SOC (no envia mensajes externos)."
    perm = "modify"
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "mensaje para el operador"},
            "level": {"type": "string", "default": "info",
                      "description": "info|warning|critical"},
        },
        "required": ["message"],
    }

    def run(self, a: dict[str, Any]) -> Any:
        message = str(a.get("message", "")).strip()
        if not message:
            return {"error": "message requerido"}
        level = str(a.get("level", "info")).strip().lower() or "info"
        return {"status": "notified", "channel": "operator_console",
                "level": level, "message": message}
