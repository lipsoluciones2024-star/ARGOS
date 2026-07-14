from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeKillProcessTool(ProposeActionTool):
    name = "propose_kill_process"
    description = "Propone terminar un proceso por PID (gobernado por el switch de autonomia)."
    action = "kill_process"
    parameters = {
        "type": "object",
        "properties": {"pid": {"type": "integer", "description": "PID del proceso a terminar"}},
        "required": ["pid"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        pid = a.get("pid")
        return str(pid), {"pid": pid}
