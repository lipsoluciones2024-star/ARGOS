from __future__ import annotations

from typing import Any

from argos.ai.tools.plugins._action_base import ProposeActionTool
from argos.ai.tools.registry import register_tool


@register_tool
class ProposeMemorySnapshotTool(ProposeActionTool):
    name = "propose_memory_snapshot"
    description = "Propone capturar un volcado de memoria de un proceso (gobernado por el switch)."
    action = "memory_snapshot"
    parameters = {
        "type": "object",
        "properties": {"pid": {"type": "integer", "description": "PID del proceso a volcar"}},
        "required": ["pid"],
    }

    def _extract(self, a: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        pid = a.get("pid")
        return str(pid), {"pid": pid}
